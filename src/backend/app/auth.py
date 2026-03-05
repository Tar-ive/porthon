import os
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_swagger_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    mode: str
    livemode: bool
    persona_id: str
    temperature: float
    demo: bool = False


def parse_auth(auth_header: str | None) -> AuthContext:
    if os.environ.get("PORTTHON_OFFLINE_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return AuthContext(
            mode="demo", livemode=False, persona_id="p05", temperature=0.0, demo=True
        )
    if auth_header and auth_header.startswith("Bearer sk_demo_"):
        return AuthContext(
            mode="demo", livemode=False, persona_id="p05", temperature=0.0, demo=True
        )
    if auth_header and auth_header.startswith("Bearer sk_live_"):
        return AuthContext(
            mode="live", livemode=True, persona_id="p05", temperature=0.7
        )
    return AuthContext(mode="live", livemode=True, persona_id="p05", temperature=0.7)


def get_livemode(auth_header: str | None) -> bool:
    return parse_auth(auth_header).livemode


def get_persona_id(auth_header: str | None) -> str:
    return parse_auth(auth_header).persona_id


def get_temperature(auth_header: str | None) -> float:
    return parse_auth(auth_header).temperature


def get_mode(auth_header: str | None) -> str:
    return parse_auth(auth_header).mode


def is_demo_mode(auth_header: str | None) -> bool:
    return parse_auth(auth_header).demo


def swagger_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_swagger_bearer),
) -> str | None:
    """OpenAPI-visible bearer dependency for Swagger Authorize button."""
    if creds is None:
        return None
    return f"Bearer {creds.credentials}"
