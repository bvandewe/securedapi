description = """
## Sample App secured by Oauth2 with Keycloak

### Alpha Release Aug 30, 2023

---

_Repository_: [bvandewe/securedapi](https://github.com/bvandewe/securedapi)

This simple API includes endpoints that are secured with different levels:

- Public: No Authentication
- Restricted:
  - Authenticated User
  - Authenticated User + Role
  - Authenticated User + Claim type
  - Authenticated User + Claim type:value
  - Authenticated User + Claims [{type:value}, {type:value}]
"""


tags_metadata = [
    {
        "name": "Unrestricted",
        "description": "Routes that are available publicly",
        "externalDocs": {
            "description": "Public docs",
            "url": "https://github.com/bvandewe/securedapi",
        },
    },
    {
        "name": "Restricted",
        "description": "Routes that are restricted based on claims from JWT",
        "externalDocs": {
            "description": "Restricted docs",
            "url": "https://github.com/bvandewe/securedapi",
        },
    }
]
