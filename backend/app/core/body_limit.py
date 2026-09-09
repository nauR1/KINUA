from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound request bodies before multipart/JSON parsing, including chunked uploads."""

    def __init__(self, app, max_bytes: int, video_bytes: int | None = None):
        self.app, self.max_bytes = app, max_bytes
        self.video_bytes = video_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        limit = (
            self.video_bytes
            if self.video_bytes and scope.get("path", "").endswith("/videos")
            else self.max_bytes
        )
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                response = JSONResponse(
                    {"detail": "Requisição excede o limite de tamanho."},
                    status_code=413,
                )
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        chunks.clear()
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
