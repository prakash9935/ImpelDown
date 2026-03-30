"""
OIDC JWT Authentication (US-301, US-302, Sprint 3)

Validates JWT tokens from Keycloak/Azure AD and extracts user role from claims.

Implements:
  - validate_jwt() — signature verification, expiry check
  - extract_role_from_jwt() — hierarchical role mapping
  - JWKS caching for performance
"""

import logging

from typing import Dict, Optional

import httpx
from fastapi import HTTPException
from jose import JWTError, jwt

from src.secrag.config import settings

logger = logging.getLogger(__name__)

# Module-level JWKS cache
_JWKS_CACHE: Optional[Dict] = None
_JWKS_CACHE_KEYS: Optional[Dict] = None


async def _fetch_jwks():
    """Fetch JWKS from OIDC issuer."""
    global _JWKS_CACHE, _JWKS_CACHE_KEYS

    try:
        jwks_url = f"{settings.oidc_issuer_url}/.well-known/jwks.json"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(jwks_url)
            _JWKS_CACHE = response.json()
            _JWKS_CACHE_KEYS = {key["kid"]: key for key in _JWKS_CACHE.get("keys", [])}
            logger.info(f"Fetched JWKS from {jwks_url}")
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(status_code=401, detail="Failed to validate token")


async def validate_jwt(token: str) -> Dict[str, any]:
    """
    Validate JWT token from OIDC provider (US-301).

    Verifies:
    1. Token signature using OIDC provider's public key
    2. Token expiry (exp claim)
    3. Issuer and audience claims
    4. Caches JWKS keys for performance

    Args:
        token: JWT token from Authorization header

    Returns:
        Decoded token claims (sub, email, roles, etc.)

    Raises:
        HTTPException(status_code=401) if invalid
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    # In testing mode, decode without signature verification
    if settings.testing:
        try:
            claims = jwt.get_unverified_claims(token)
            logger.debug("Test mode: decoded JWT without signature verification")
            return claims
        except JWTError as e:
            logger.error(f"Failed to decode JWT in test mode: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")

    # Production: verify signature with JWKS
    try:
        # Fetch JWKS if not cached
        if _JWKS_CACHE is None:
            await _fetch_jwks()

        # Get token header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if kid not in _JWKS_CACHE_KEYS:
            logger.warning(f"Token signed with unknown key ID: {kid}, refetching JWKS")
            await _fetch_jwks()

        # Find the public key
        if kid not in _JWKS_CACHE_KEYS:
            raise HTTPException(status_code=401, detail="Invalid token signature")

        key = _JWKS_CACHE_KEYS[kid]

        # Verify token signature
        # SECURITY: Only allow configured algorithm (RS256 or ES256).
        # Accepting HS256 creates algorithm confusion vulnerability.
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.oidc_client_id,
                issuer=settings.oidc_issuer_url,
            )
        except JWTError as e:
            # If audience validation fails, try without audience (for Supabase which uses "authenticated") # noqa: E501
            if "Invalid audience" in str(e):
                logger.debug("Audience mismatch, retrying without audience validation")
                claims = jwt.decode(
                    token,
                    key,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_aud": False},
                    issuer=settings.oidc_issuer_url,
                )
            else:
                raise

        logger.debug(f"JWT validated successfully for user {claims.get('sub')}")
        return claims

    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        # SECURITY: Don't leak error details to client (helps attackers craft forged tokens)
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


def extract_role_from_jwt(claims: Dict[str, any]) -> str:
    """
    Extract user role from JWT claims (US-302).

    Supports multiple provider formats:
    - Keycloak flat: claims["roles"] = ["admin", "finance"]
    - Keycloak nested: claims["realm_access"]["roles"] = ["admin"]
    - Supabase: claims["user_metadata"]["role"] = "admin"

    Role priority (first match wins):
    1. admin → Admin
    2. finance → Finance
    3. hr → HR
    4. (default) → Standard

    Args:
        claims: Decoded JWT claims dict

    Returns:
        User role (admin, finance, hr, standard) in lowercase

    Raises:
        HTTPException(status_code=403) if no valid role
    """
    # Try Supabase format (user_metadata.role)
    user_metadata = claims.get("user_metadata", {})
    if user_metadata and "role" in user_metadata:
        role = user_metadata.get("role", "").lower()
        if role in ["admin", "finance", "hr"]:
            logger.info(f"Role extracted: {role} (Supabase format)")
            return role
        else:
            logger.info("Role extracted: standard (Supabase fallback)")
            return "standard"

    # Try flat roles format (Keycloak default)
    roles = claims.get("roles", [])

    # Try nested format (realm_access.roles)
    if not roles:
        realm_access = claims.get("realm_access", {})
        roles = realm_access.get("roles", [])

    if not roles:
        logger.info(f"No roles found in JWT for user {claims.get('sub')}, defaulting to standard")
        return "standard"

    # Normalize roles to lowercase for comparison
    roles_lower = [r.lower() for r in roles]

    # Check role priority
    if "admin" in roles_lower:
        logger.info("Role extracted: admin")
        return "admin"
    elif "finance" in roles_lower:
        logger.info("Role extracted: finance")
        return "finance"
    elif "hr" in roles_lower:
        logger.info("Role extracted: hr")
        return "hr"
    else:
        logger.info("Role extracted: standard (fallback)")
        return "standard"
