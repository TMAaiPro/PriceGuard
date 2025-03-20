from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class JWTScheme(OpenApiAuthenticationExtension):
    target_class = 'rest_framework_simplejwt.authentication.JWTAuthentication'
    name = 'JWT Bearer Auth'
    
    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            bearer_format='JWT',
            description=(
                'JWT token authentication. Get a token from the /api/token/ endpoint. '
                'Include the token in the Authorization header as: Bearer <token>'
            )
        )
