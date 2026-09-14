from app.observability.logging import configure_logging
from app.observability.metrics import configure_metrics
from app.observability.tracing import configure_observability


def init_observability(
    app,
    engine=None,
):
    configure_logging()

    configure_metrics()

    configure_observability(
        app=app,
        engine=engine,
    )