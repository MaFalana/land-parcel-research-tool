"""
Azure Entra ID (formerly Azure AD) authentication
"""
import os
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from functools import lru_cache


# Environment variables
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

# Azure AD endpoints
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"

# Security scheme
security = HTTPBearer(auto_error=False)


@lru_cache()
def get_jwks_client():
    """Get cached JWKS client for token validation"""
    if not TENANT_ID:
        return None
    return PyJWKClient(JWKS_URL)


def verify_token(token: str) -> dict:
    """
    Verify JWT token from Azure Entra ID
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        jwks_client = get_jwks_client()
        if not jwks_client:
            raise HTTPException(
                status_code=500,
                detail="Authentication not configured (missing AZURE_TENANT_ID)"
            )
        
        # Get signing key
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True
            }
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token audience"
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token issuer"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[dict]:
    """
    Dependency to get current authenticated user
    
    Returns user info from token if authentication is enabled,
    otherwise returns None (allowing unauthenticated access)
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    # If auth is not required, allow access
    if not REQUIRE_AUTH:
        return None
    
    # If auth is required but no credentials provided
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user info
    user_info = {
        "user_id": payload.get("oid"),  # Object ID (unique user identifier)
        "email": payload.get("preferred_username") or payload.get("email"),
        "name": payload.get("name"),
        "tenant_id": payload.get("tid"),
        "roles": payload.get("roles", []),
        "scopes": payload.get("scp", "").split() if payload.get("scp") else []
    }
    
    return user_info


async def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Dependency that requires authentication
    
    Use this for routes that must be authenticated even if REQUIRE_AUTH=false
    
    Usage:
        @app.get("/admin")
        async def admin_route(user: dict = Depends(require_auth)):
            return {"user": user}
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_role(required_role: str):
    """
    Dependency factory that requires a specific role
    
    Usage:
        @app.get("/admin")
        async def admin_route(user: dict = Depends(require_role("Admin"))):
            return {"user": user}
    """
    async def role_checker(user: dict = Depends(require_auth)) -> dict:
        roles = user.get("roles", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Required role '{required_role}' not found"
            )
        return user
    
    return role_checker
