import httpx
import logging
import jwt

from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import ExpiredSignatureError, MissingRequiredClaimError
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseSettings, SecretStr, AnyHttpUrl


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ApiSettings(BaseSettings):
    """Settings used to configure authentication authority."""
    app_name: str = "Secured API"
    jwt_authority_base_url: AnyHttpUrl = AnyHttpUrl(url="localhost:8080", scheme="http")
    jwt_authority_base_url_internal: AnyHttpUrl = AnyHttpUrl(url="keycloak", scheme="http")
    jwt_public_key: str | None = None  # set by
    auth_realm: str = "myrealm"
    client_id: str = "myclientid"
    client_secret: SecretStr = SecretStr("myclientsecret")
    required_scopes: str = "requiredscope"
    expected_audience: str = "expectedaudience"


settings = ApiSettings()

swagger_ui_init_oauth = {
    "appName": settings.app_name,
    "realm": settings.auth_realm,
    "clientId": settings.client_id,
    "clientSecret": settings.client_secret.get_secret_value(),
    "scope": settings.required_scopes
}
expected_audience = settings.expected_audience

app = FastAPI(title="Secured API",
              docs_url="/api/docs",
              redoc_url=None,
              openapi_url="/api/v1/oas.json",
              swagger_ui_init_oauth=swagger_ui_init_oauth)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.jwt_authority_base_url}/auth/realms/{settings.auth_realm}/protocol/openid-connect/token")


async def get_public_key():
    # http://localhost:8080 wont work when in Docker Desktop!
    base_url = settings.jwt_authority_base_url_internal if settings.jwt_authority_base_url_internal else settings.jwt_authority_base_url
    jwks_url = f"{base_url}/auth/realms/{settings.auth_realm}/protocol/openid-connect/certs"
    log.debug(f"get_public_key from {jwks_url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        keys = response.json()["keys"]
        for key in keys:
            if key.get("alg") == "RS256":
                # https://github.com/jpadilla/pyjwt/issues/359#issuecomment-406277697
                public_key = RSAAlgorithm.from_jwk(key)
                return public_key
        raise Exception("No key with 'alg' value of 'RS256' found")


def validate_token(token: str = Depends(oauth2_scheme)):
    if not settings.jwt_public_key:
        raise Exception("Token can not be valided as the JWT Public Key is unknown!")
    try:
        payload = jwt.decode(jwt=token, key=settings.jwt_public_key, algorithms=["RS256"], options={"verify_aud": False})
        # payload = jwt.decode(token=token, key=settings.jwt_public_key, algorithms=["RS256"], audience=settings.expected_audience)

        def is_subset(arr1, arr2):
            set1 = set(arr1)
            set2 = set(arr2)
            return set1.issubset(set2) or set1 == set2

        if "scope" in payload:
            required_scopes = settings.required_scopes.split()
            token_scopes = payload["scope"].split()
            if not is_subset(token_scopes, required_scopes):
                raise HTTPException(status_code=403, detail="Insufficient scope")

        if settings.expected_audience not in payload["aud"]:
            raise HTTPException(status_code=401, detail="Invalid audience")

        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except MissingRequiredClaimError:
        raise HTTPException(status_code=401, detail="JWT claims validation failed")
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=f"Invalid token: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def has_custom_claim(token: dict = Depends(validate_token)):
    if "custom_claim" in token and "my_claim_value" in token["custom_claim"]:
        return token
    else:
        raise HTTPException(status_code=403, detail="Missing or invalid custom_claim")


def has_role(role: str):
    def decorator(token: dict = Depends(validate_token)):
        if "role" in token and role in token["role"]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid role {role}")
    return decorator


def has_required_claim(claim_name: str, claim_value: str):
    def decorator(token: dict = Depends(validate_token)):
        if claim_name in token and claim_value in token[claim_name]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
    return decorator


@app.on_event("startup")
async def startup_event():
    settings.jwt_public_key = await get_public_key()  # pyright: ignore


@app.get("/public")
async def public_endpoint():
    return {"message": "This is a public test route."}


@app.get("/protected")
async def protected_route(token: dict = Depends(validate_token)):
    return {"message": "This is a protected route", "token": token}


@app.get("/restricted-to-role")
async def restricted_by_role(token: dict = Depends(has_role(role="tester"))):
    return {"message": "This is a restricted route for role 'tester'", "token": token}


@app.get("/custom_claim_protected")
async def custom_claim_protected(token: dict = Depends(has_custom_claim)):
    return {"message": "This is a protected route with custom claim check", "token": token}


@app.get("/specific_claim_protected")
async def specific_claim_protected(token: dict = Depends(has_required_claim(claim_name="custom_claim", claim_value="my_claim_value"))):
    return {"message": "This is a protected route with specific claim check", "token": token}
