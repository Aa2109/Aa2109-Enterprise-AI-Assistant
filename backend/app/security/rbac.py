"""Role -> permission mapping.

Kept as a leaf module (imports only ``models``) so both ``auth`` and
``permissions`` can import it without creating a circular dependency.
"""

from app.security.models import Permission, Role


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.USER: {
        Permission.CHAT,
        Permission.RAG_READ,
    },
    Role.ANALYST: {
        Permission.CHAT,
        Permission.RAG_READ,
        Permission.RESEARCH,
        Permission.DATA_READ,
    },
    Role.ADMIN: {
        Permission.CHAT,
        Permission.RAG_READ,
        Permission.RESEARCH,
        Permission.DATA_READ,
        Permission.DATA_WRITE,
        Permission.ADMIN,
    },
}


def permissions_for_role(role: Role) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())