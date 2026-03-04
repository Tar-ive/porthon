from dataclasses import dataclass
from typing import Any


@dataclass
class AuthContext:
    mode: str
    livemode: bool
    persona_id: str
    temperature: float
    demo: bool = False


def parse_auth(auth_header: str | None) -> AuthContext:
    if not auth_header:
        return AuthContext(
            mode="live", livemode=True, persona_id="p05", temperature=0.7
        )

    if auth_header.startswith("Bearer sk_live_"):
        return AuthContext(
            mode="live", livemode=True, persona_id="p05", temperature=0.7
        )
    elif auth_header.startswith("Bearer sk_test_"):
        return AuthContext(
            mode="test", livemode=False, persona_id="p05", temperature=0.0
        )
    elif auth_header.startswith("Bearer sk_demo_p5"):
        return AuthContext(
            mode="demo", livemode=False, persona_id="p05", temperature=0.0, demo=True
        )

    return AuthContext(mode="live", livemode=True, persona_id="p05", temperature=0.7)


def get_livemode(auth_header: str | None) -> bool:
    return parse_auth(auth_header).livemode


def get_persona_id(auth_header: str | None) -> str:
    return parse_auth(auth_header).persona_id


def get_temperature(auth_header: str | None) -> float:
    return parse_auth(auth_header).temperature


def is_demo_mode(auth_header: str | None) -> bool:
    return parse_auth(auth_header).demo
