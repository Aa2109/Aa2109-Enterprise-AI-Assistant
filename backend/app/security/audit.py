import logging


logger = logging.getLogger("security")


def audit_security_event(
    *,
    event: str,
    user_id: str | None,
    resource: str | None = None,
    action: str | None = None,
    allowed: bool = True,
) -> None:
    logger.info(
        "security_event",
        extra={
            "event": event,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
        },
    )
