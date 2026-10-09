"""
tests/test_websocket.py — Unit and integration tests for WebSocket Echo Server
"""
import asyncio
import pytest
import websockets
from server import echo_handler


def test_websocket_echo_server():
    """Verify that messages sent to echo_handler are echoed back prefixed with 'ECHO: '."""
    async def _run_test():
        async with websockets.serve(echo_handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            uri = f"ws://127.0.0.1:{port}"

            async with websockets.connect(uri) as client:
                test_messages = [
                    "Hello Swarelic",
                    "Testing VoiceCallConsumer pattern",
                    "12345!@#$%"
                ]

                for msg in test_messages:
                    await client.send(msg)
                    response = await asyncio.wait_for(client.recv(), timeout=2.0)
                    assert response == f"ECHO: {msg}"

    asyncio.run(_run_test())
