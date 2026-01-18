"""Auth gateway stub endpoints (passkeys + sessions)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from shared.auth import (
    AuthSession,
    build_webauthn_challenge,
    build_webauthn_user_handle,
    get_auth_store,
    extract_session_token,
)
from shared.tenancy import get_nats_credentials, get_nats_ws_url

router = APIRouter()


class PasskeyRegistrationOptionsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    username: Optional[str] = None
    display_name: Optional[str] = None
    rp_id: Optional[str] = None
    origin: Optional[str] = None


class PasskeyRegistrationVerifyRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    challenge_id: str = Field(..., min_length=1)
    credential: dict = Field(default_factory=dict)
    client_label: Optional[str] = None


class PasskeyAuthenticationOptionsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    rp_id: Optional[str] = None


class PasskeyAuthenticationVerifyRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    challenge_id: str = Field(..., min_length=1)
    credential: dict = Field(default_factory=dict)
    client_label: Optional[str] = None


class SessionRevokeRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


def require_session(request: Request) -> AuthSession:
    token = extract_session_token(request.headers)
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    session = get_auth_store().verify_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return session


@router.post("/passkeys/register/options")
def passkey_register_options(payload: PasskeyRegistrationOptionsRequest):
    store = get_auth_store()
    store.ensure_user(payload.user_id, payload.username, payload.display_name)
    challenge = store.create_challenge(payload.user_id, "registration", payload.rp_id)

    public_key = {
        "challenge": build_webauthn_challenge(challenge.challenge),
        "rp": {
            "name": "ChoirOS",
            "id": challenge.rp_id,
        },
        "user": {
            "id": build_webauthn_user_handle(payload.user_id),
            "name": payload.username or payload.user_id,
            "displayName": payload.display_name or payload.username or payload.user_id,
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},
            {"type": "public-key", "alg": -257},
        ],
        "timeout": 60000,
        "attestation": "none",
        "authenticatorSelection": {
            "residentKey": "preferred",
            "userVerification": "preferred",
        },
    }

    return {
        "challenge_id": challenge.challenge_id,
        "publicKey": public_key,
    }


@router.post("/passkeys/register/verify")
def passkey_register_verify(payload: PasskeyRegistrationVerifyRequest):
    store = get_auth_store()
    challenge = store.consume_challenge(payload.challenge_id, "registration")
    if not challenge:
        raise HTTPException(status_code=400, detail="Invalid or expired challenge")

    credential_id = payload.credential.get("id") or payload.credential.get("rawId")
    if not credential_id:
        credential_id = payload.challenge_id

    store.register_passkey(payload.user_id, credential_id)
    session, token = store.create_session(payload.user_id, payload.client_label)

    return {
        "session": session.to_dict(),
        "token": token,
    }


@router.post("/passkeys/authenticate/options")
def passkey_authenticate_options(payload: PasskeyAuthenticationOptionsRequest):
    store = get_auth_store()
    store.ensure_user(payload.user_id)
    challenge = store.create_challenge(payload.user_id, "authentication", payload.rp_id)
    passkeys = store.list_passkeys(payload.user_id)

    allow_credentials = [
        {"type": "public-key", "id": record.credential_id}
        for record in passkeys
    ]

    public_key = {
        "challenge": build_webauthn_challenge(challenge.challenge),
        "rpId": challenge.rp_id,
        "timeout": 60000,
        "userVerification": "preferred",
        "allowCredentials": allow_credentials,
    }

    return {
        "challenge_id": challenge.challenge_id,
        "publicKey": public_key,
    }


@router.post("/passkeys/authenticate/verify")
def passkey_authenticate_verify(payload: PasskeyAuthenticationVerifyRequest):
    store = get_auth_store()
    challenge = store.consume_challenge(payload.challenge_id, "authentication")
    if not challenge:
        raise HTTPException(status_code=400, detail="Invalid or expired challenge")

    passkeys = {record.credential_id for record in store.list_passkeys(payload.user_id)}
    if not passkeys:
        raise HTTPException(status_code=404, detail="No passkeys registered for user")

    credential_id = payload.credential.get("id") or payload.credential.get("rawId")
    if credential_id not in passkeys:
        raise HTTPException(status_code=401, detail="Unknown credential")

    session, token = store.create_session(payload.user_id, payload.client_label)

    return {
        "session": session.to_dict(),
        "token": token,
    }


@router.get("/sessions")
def list_sessions(session: AuthSession = Depends(require_session)):
    store = get_auth_store()
    sessions = store.list_sessions(session.user_id)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.post("/sessions/revoke")
def revoke_session(payload: SessionRevokeRequest, session: AuthSession = Depends(require_session)):
    store = get_auth_store()
    revoked = store.revoke_session(session.user_id, payload.session_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"revoked": True}


@router.get("/nats/credentials")
def get_nats_credentials_for_session(session: AuthSession = Depends(require_session)):
    creds = get_nats_credentials(session.user_id, role="web")
    if not creds:
        raise HTTPException(status_code=404, detail="No NATS credentials for user")
    return {
        "servers": get_nats_ws_url(),
        "user": creds.user,
        "password": creds.password,
        "subject_prefix": creds.subject_prefix,
        "user_id": session.user_id,
    }
