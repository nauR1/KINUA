from starlette.responses import JSONResponse


class BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """Bound request bodies while preserving ASGI streaming semantics."""

    def __init__(self, app, max_bytes: int, video_bytes: int | None = None):
        self.app, self.max_bytes = app, max_bytes
        self.video_bytes = video_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)

        limit = (
            self.video_bytes
            if self.video_bytes and scope.get("path", "").endswith("/videos")
            else self.max_bytes
        )
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > limit:
                    raise BodyTooLarge()
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            response = JSONResponse(
                {"detail": "Requisição excede o limite de tamanho."},
                status_code=413,
            )
            await response(scope, receive, send)
