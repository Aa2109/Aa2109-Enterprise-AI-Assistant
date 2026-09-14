from uuid import uuid4

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)

from app.observability.context import (
    set_request_id,
)


class RequestIDMiddleware(
    BaseHTTPMiddleware
):

    async def dispatch(
        self,
        request,
        call_next,
    ):

        request_id = request.headers.get(
            "X-Request-ID"
        )

        if not request_id:
            request_id = str(
                uuid4()
            )

        set_request_id(
            request_id
        )

        # Handlers and their exception paths read request_id from
        # request.state (e.g. /health, /ready) as well as from the
        # contextvar above — make sure both sources agree.
        request.state.request_id = request_id

        response = await call_next(
            request
        )

        response.headers[
            "X-Request-ID"
        ] = request_id

        return response