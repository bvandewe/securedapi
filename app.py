import httpx
import logging
import jwt
import typing

from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import ExpiredSignatureError, MissingRequiredClaimError
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseSettings, SecretStr, AnyHttpUrl

from openapi_descr import description, tags_metadata


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ApiSettings(BaseSettings):
    """Settings used to configure authentication authority."""
    app_version: str = "0.1.0"
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
              version=settings.app_version,
              description=description,
              openapi_tags=tags_metadata,
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


def has_role(role: str):
    def decorator(token: dict = Depends(validate_token)):
        if "role" in token and role in token["role"]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid role {role}")
    return decorator


def has_claim(claim_name: str):
    def decorator(token: dict = Depends(validate_token)):
        if claim_name in token:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
    return decorator


def has_single_claim_value(claim_name: str, claim_value: str):
    def decorator(token: dict = Depends(validate_token)):
        if claim_name in token and claim_value in token[claim_name]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
    return decorator


def has_multiple_claims_value(claims: typing.Dict[str, str]):
    def decorator(token: dict = Depends(validate_token)):
        for claim_name, claim_value in claims.items():
            if claim_name not in token or claim_value not in token[claim_name]:
                raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
        return token
    return decorator


@app.on_event("startup")
async def startup_event():
    settings.jwt_public_key = await get_public_key()  # pyright: ignore


@app.get(path="/api/v1/public",
         tags=['Unrestricted'],
         operation_id="no_auth",
         response_description="A simple message object")
async def no_auth():
    """This route is publicly available, that is: it doesnt require any token.

    Returns:
        Dict: Simple message
    """
    return {"message": "This route is publicly available."}


@app.get(path="/api/v1/secured/valid_user",
         tags=['Restricted'],
         operation_id="requires_authenticated_user",
         response_description="A simple message object")
async def requires_authenticated_user(token: dict = Depends(validate_token)):
    """This route expects a valid token, that is: the user is authenticated.

    Args:
        token (dict, optional): The JWT. Defaults to Depends(validate_token).

    Returns:
        Dict: Simple message and the token content
    """
    return {"message": "This is a protected route", "token": token}


@app.get(path="/api/v1/secured/role",
         tags=['Restricted'],
         operation_id="requires_tester_role",
         response_description="A simple message object")
async def requires_tester_role(token: dict = Depends(has_role(role="tester"))):
    """This route expects a valid token that includes the role `"tester"` in the `role` array; that is:
    ```
    ...
    "role": [
      "tester"
    ]
    ...
    ```
    Args:
        token (dict, optional): The JWT. Defaults to Depends(validate_token).

    Returns:
        Dict: Simple message and the token content
    """
    return {"message": "This route is restricted to users with the role 'tester'", "token": token}


@app.get(path="/api/v1/secured/claim",
         tags=['Restricted'],
         operation_id="requires_custom_claim",
         response_description="A simple message object")
async def requires_custom_claim(token: dict = Depends(has_claim(claim_name="custom_claim"))):
    """This route expects a valid token that includes the presence of the custom claim `custom_claim` (**with any value**); that is:
    ```
    ...
    "custom_claim": [],
    ...
    ```

    Args:
        token (dict, optional): The JWT. Defaults to Depends(validate_token).

    Returns:
        Dict: Simple message and the token content
    """
    return {"message": "This route is restricted to users with a custom claim` custom_claim`", "token": token}


@app.get(path="/api/v1/secured/claim_value",
         tags=['Restricted'],
         operation_id="requires_custom_claim_with_specific_value",
         response_description="A simple message object")
async def requires_custom_claim_with_specific_value(token: dict = Depends(has_single_claim_value(claim_name="custom_claim", claim_value="my_claim_value"))):
    """This route expects a valid token that includes the presence of the custom claim `custom_claim` with the value `my_claim_value`; that is:
    ```
    ...
    "custom_claim": [
        "my_claim_value"
    ],
    ...
    ```

    Args:
        token (dict, optional): The JWT. Defaults to Depends(validate_token).

    Returns:
        Dict: Simple message and the token content
    """
    return {"message": "This route is restricted to users with the custom claim:value `custom_claim: my_claim_value`", "token": token}


@app.get(path="/api/v1/secured/claims_values",
         tags=['Restricted'],
         operation_id="requires_multiple_claims_each_with_specific_value",
         response_description="A simple message object")
async def requires_multiple_claims_each_with_specific_value(token: dict = Depends(has_multiple_claims_value(claims={
    "custom_claim": "my_claim_value",
    "role": "tester"
}))):
    """This route expects a valid token that includes the presence of multiple custom claims, each with a specific value; that is:
    ```
    ...
    "custom_claim": [
        "my_claim_value"
    ],
    "role": [
        "tester"
    ]
    ...
    ```

    Args:
        token (dict, optional): The JWT. Defaults to Depends(validate_token).

    Returns:
        Dict: Simple message and the token content
    """
    return {"message": "This route is restricted to users with custom claims `custom_claim: my_claim_value, role: tester`", "token": token}
