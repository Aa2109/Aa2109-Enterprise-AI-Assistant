# app/observability/tracing.py

import logging

from opentelemetry import trace

from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,
)

from opentelemetry.instrumentation.sqlalchemy import (
    SQLAlchemyInstrumentor,
)

from opentelemetry.sdk.resources import (
    Resource,
)

from opentelemetry.sdk.trace import (
    TracerProvider,
)

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)


logger = logging.getLogger(__name__)


TRACER_NAME = "enterprise-ai-assistant"
SERVICE_NAME = "enterprise-ai-assistant"


def configure_tracing() -> None:
    """
    Configure the OpenTelemetry tracer provider.
    Call once during application startup.
    """

    current_provider = trace.get_tracer_provider()

    # Don't configure twice.
    if isinstance(current_provider, TracerProvider):
        return

    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
        }
    )

    provider = TracerProvider(
        resource=resource
    )

    exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",
        insecure=True,
    )

    span_processor = BatchSpanProcessor(
        exporter
    )

    provider.add_span_processor(
        span_processor
    )

    trace.set_tracer_provider(
        provider
    )

    logger.info(
        "OpenTelemetry tracer provider initialized"
    )


def get_tracer():
    return trace.get_tracer(
        TRACER_NAME
    )


def instrument_fastapi(app) -> None:

    FastAPIInstrumentor.instrument_app(
        app
    )

    logger.info(
        "FastAPI OpenTelemetry instrumentation enabled"
    )


def instrument_sqlalchemy(engine) -> None:

    if engine is None:
        return

    SQLAlchemyInstrumentor().instrument(
        engine=engine
    )

    logger.info(
        "SQLAlchemy OpenTelemetry instrumentation enabled"
    )


def configure_observability(
    app=None,
    engine=None,
) -> None:

    # 1. Configure provider/exporter
    configure_tracing()

    # 2. FastAPI instrumentation
    if app is not None:

        instrument_fastapi(
            app
        )

    # 3. SQLAlchemy instrumentation
    if engine is not None:

        instrument_sqlalchemy(
            engine
        )