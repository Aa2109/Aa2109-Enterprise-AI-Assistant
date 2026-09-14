"""Security package.

Re-exports the public security API. Exports resolve lazily via
PEP 562 ``__getattr__`` so the package initializes without triggering
circular imports between submodules (notably ``auth`` <-> ``permissions``).
"""

from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "Role": ("app.security.models", "Role"),
    "Permission": ("app.security.models", "Permission"),
    "UserContext": ("app.security.models", "UserContext"),
    "get_current_user": ("app.security.auth", "get_current_user"),
    "require_permission": (
        "app.security.permissions",
        "require_permission",
    ),
    "permissions_for_role": (
        "app.security.rbac",
        "permissions_for_role",
    ),
    "ROLE_PERMISSIONS": (
        "app.security.rbac",
        "ROLE_PERMISSIONS",
    ),
    "create_access_token": ("app.security.jwt", "create_access_token"),
    "decode_access_token": ("app.security.jwt", "decode_access_token"),
    "require_tool_permission": (
        "app.security.guards",
        "require_tool_permission",
    ),
    "detect_prompt_injection": (
        "app.security.prompt_guard",
        "detect_prompt_injection",
    ),
    "validate_user_prompt": (
        "app.security.prompt_guard",
        "validate_user_prompt",
    ),
    "audit_security_event": (
        "app.security.audit",
        "audit_security_event",
    ),
}


def __getattr__(name: str) -> Any:
    import importlib

    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr)

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


__all__ = list(_LAZY_EXPORTS)