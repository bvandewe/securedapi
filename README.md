# Secure API with OAuth2

Some API endpoints may require different types or levels of Authorization; for example: 

- the user is authenticated (i.e. has a valid token): see 
- the user has a specific role (i.e. the token has a predefined value in the `role` array):
-  the user has a specific custom permission (i.e. the token has a specific `type:value`):

![Demo](assets/demo.gif)

TODO

## Usage

1. Install/Start Docker Desktop
2. Run `docker-compose.debug.yml` with vscode (Right click > `Compose Up`)
3. Navigate to http://localhost:8080
4. Navigate to http://localhost:8893
5. Try any endpoint and see the 401 Unauthorized for protected endpoints
6. Authenticate/Authorize with `test@test.com:test` (cf. green `Authorize` button in SwaggerUI top-right)
7. Try again a protected endpoint

## Realm Config

See [realm-config.json](realm-config.json)!

Name: `myrealm`

### Client `secureapi`

The client config is very simple and enables `Resource Owner Password Credentials Grant`.

With this grant type, the app asks the end-user for a username and password once, and then it can use that information to request an access token from the Authorization Server. Once it gets the access token, it can use it to access the end-user data or perform actions without asking the user for a password again and again.

```json
{
   "clientId": "secureapi",
   "secret": "380577f5-3262-4a05-a84c-9e98cc276f85",
   "redirectUris": [
       "*"
   ],
   "directAccessGrantsEnabled": true,
   "webOrigins": [
       "*"
   ],
   "defaultClientScopes": [
       "web-origins",
       "profile",
       "roles",
       "api",
       "email"
   ]
}
```

### Client Scope `api`

```json
{
   "name": "api",
   "description": "Expected scope for secureapi test app",
   "protocol": "openid-connect",
   "attributes": {
       "include.in.token.scope": "true"
   },
   "protocolMappers": [
       {
           "name": "api audience",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-audience-mapper",
           "consentRequired": false,
           "config": {
               "id.token.claim": "true",
               "access.token.claim": "true",
               "included.custom.audience": "api"
           }
       },
       {
           "name": "User Realm Role",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-usermodel-realm-role-mapper",
           "consentRequired": false,
           "config": {
               "multivalued": "true",
               "userinfo.token.claim": "true",
               "id.token.claim": "true",
               "access.token.claim": "true",
               "claim.name": "role",
               "jsonType.label": "String"
           }
       },
       {
           "name": "custom_claim",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-usermodel-attribute-mapper",
           "consentRequired": false,
           "config": {
               "aggregate.attrs": "true",
               "multivalued": "true",
               "userinfo.token.claim": "true",
               "user.attribute": "custom_claim",
               "id.token.claim": "true",
               "access.token.claim": "true",
               "claim.name": "custom_claim",
               "jsonType.label": "String"
           }
       },
       {
           "name": "full name",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-full-name-mapper",
           "consentRequired": false,
           "config": {
               "id.token.claim": "true",
               "access.token.claim": "true",
               "userinfo.token.claim": "true"
           }
       },
       {
           "name": "username",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-usermodel-property-mapper",
           "consentRequired": false,
           "config": {
               "userinfo.token.claim": "true",
               "user.attribute": "username",
               "id.token.claim": "true",
               "access.token.claim": "true",
               "claim.name": "preferred_username",
               "jsonType.label": "String"
           }
       },
       {
           "name": "email",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-usermodel-property-mapper",
           "consentRequired": false,
           "config": {
               "userinfo.token.claim": "true",
               "user.attribute": "email",
               "id.token.claim": "true",
               "access.token.claim": "true",
               "claim.name": "email",
               "jsonType.label": "String"
           }
       },
       {
           "name": "profile",
           "protocol": "openid-connect",
           "protocolMapper": "oidc-usermodel-attribute-mapper",
           "consentRequired": false,
           "config": {
               "userinfo.token.claim": "true",
               "user.attribute": "profile",
               "id.token.claim": "true",
               "access.token.claim": "true",
               "claim.name": "profile",
               "jsonType.label": "String"
           }
       }
   ]
}

```
