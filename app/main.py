"""Sample secure API for the demo.

A tiny FastAPI service with a POST /login endpoint that mints a bearer token
against a shared client_id / client_secret pair, plus a GET /me endpoint
protected by that bearer.

Real deployments would validate against a proper identity provider; this is
for demonstrating the QA pipeline shape, not for anything security-sensitive.
"""
from __future__ import annotations

import base64
import os
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


APP_CLIENT_ID = os.environ.get("APP_CLIENT_ID", "demo-client")
APP_CLIENT_SECRET = os.environ.get("APP_CLIENT_SECRET", "demo-secret")

app = FastAPI(title="Sample Secure API", version="1.0.0")


class LoginRequest(BaseModel):
    client_id: str
    client_secret: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class MeResponse(BaseModel):
    client_id: str
    scope: str = "read:me"
    issued_at: int


def _mint_token(client_id: str) -> str:
    """Deterministic demo token — for demonstration only, not cryptographically safe."""
    payload = f"{client_id}:{int(time.time())}".encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_token(token: str) -> Optional[str]:
    try:
        padded = token + "=" * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode()
        return decoded.split(":")[0]
    except Exception:
        return None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    if req.client_id != APP_CLIENT_ID or req.client_secret != APP_CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="invalid_client")
    return LoginResponse(access_token=_mint_token(req.client_id))


@app.get("/me", response_model=MeResponse)
def me(authorization: Optional[str] = Header(default=None)) -> MeResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    token = authorization.split(" ", 1)[1]
    client_id = _decode_token(token)
    if client_id is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    return MeResponse(client_id=client_id, issued_at=int(time.time()))
