import asyncio

from app.core.body_limit import BodyLimitMiddleware


def test_chunked_body_is_rejected_before_parsing():
    called = False
    messages = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def app(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return next(incoming)

    async def send(message):
        messages.append(message)

    asyncio.run(
        BodyLimitMiddleware(app, 5)({"type": "http", "method": "POST"}, receive, send)
    )
    assert not called
    assert messages[0]["status"] == 413


def test_bounded_body_preserves_payload():
    received = []

    async def app(scope, receive, send):
        received.append(await receive())

    async def receive():
        return {"type": "http.request", "body": b"abcd", "more_body": False}

    async def send(message):
        pass

    asyncio.run(
        BodyLimitMiddleware(app, 5)({"type": "http", "method": "POST"}, receive, send)
    )
    assert received[0]["body"] == b"abcd"
