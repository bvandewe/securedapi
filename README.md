# Secure API with OAuth2

Some endpoints may require that the user is authenticated (i.e. has a valid token), or that the user belongs to a specific group (i.e. the token has a predefined value in the `role` array) or that the user has a specific permission (i.e. the token has a specific `type:value`).

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
