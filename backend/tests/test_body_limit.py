import asyncio

from app.core.body_limit import BodyLimitMiddleware


def test_chunked_body_is_rejected_while_streaming():
    started = False
    messages = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def app(scope, receive, send):
        nonlocal started
        started = True
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break

    async def receive():
        return next(incoming)

    async def send(message):
        messages.append(message)

    asyncio.run(
        BodyLimitMiddleware(app, 5)({"type": "http", "method": "POST"}, receive, send)
    )
    assert started
    assert messages[0]["status"] == 413


def test_bounded_body_preserves_streaming_chunks():
    received = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"ab", "more_body": True},
            {"type": "http.request", "body": b"cd", "more_body": False},
        ]
    )

    async def app(scope, receive, send):
        while True:
            message = await receive()
            received.append(message)
            if not message.get("more_body", False):
                break

    async def receive():
        return next(incoming)

    async def send(message):
        pass

    asyncio.run(
        BodyLimitMiddleware(app, 5)({"type": "http", "method": "POST"}, receive, send)
    )
    assert [message["body"] for message in received] == [b"ab", b"cd"]
