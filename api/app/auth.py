import os
from fastapi import Header, HTTPException

API_KEY = os.environ.get("API_KEY", "")


def require_api_key(x_api_key: str = Header(default="")):
    """Guards write endpoints. If API_KEY is unset, auth is disabled (fine for
    a trusted in-cluster network) — set API_KEY to require the header."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")
