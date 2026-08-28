import os
import secrets

from fastapi import Header, HTTPException, status

API_KEY = os.environ.get("API_KEY", "").strip()
ALLOW_INSECURE_NO_AUTH = os.environ.get("ALLOW_INSECURE_NO_AUTH", "false").lower() == "true"


def validate_auth_configuration() -> None:
    if not API_KEY and not ALLOW_INSECURE_NO_AUTH:
        raise RuntimeError(
            "API_KEY must be set. For isolated development only, explicitly set "
            "ALLOW_INSECURE_NO_AUTH=true."
        )


def require_api_key(x_api_key: str = Header(default="")):
    """Protect financial endpoints with a constant-time API-key comparison."""
    if ALLOW_INSECURE_NO_AUTH and not API_KEY:
        return
    if not API_KEY or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
