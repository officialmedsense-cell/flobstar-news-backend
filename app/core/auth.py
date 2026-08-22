"""
Authentication middleware for API endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and return user claims

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Dictionary containing user claims

    Raises:
        HTTPException: If token is invalid
    """
    try:
        token = credentials.credentials

        # Decode token
        payload = jwt.decode(
            token,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )

        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )

        logger.info("Token verified successfully", user_id=user_id)

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
        }

    except JWTError as e:
        logger.error("JWT verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Get current authenticated user

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Dictionary containing user information

    Raises:
        HTTPException: If user is not authenticated
    """
    return await verify_token(credentials)


async def require_service_role(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Require service role (admin/backend) for sensitive operations

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Dictionary containing user claims

    Raises:
        HTTPException: If user doesn't have service role
    """
    claims = await verify_token(credentials)

    if claims.get("role") != "service_role":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service role required for this operation"
        )

    return claims
