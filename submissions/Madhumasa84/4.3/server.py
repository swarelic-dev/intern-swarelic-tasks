#!/usr/bin/env python3
"""
server.py — WebSocket Echo Server for Exercise 4.3

Accepts WebSocket connections and echoes back every received message
prefixed with "ECHO: ". Demonstrates the fundamental WebSocket communication
pattern utilized by SCAI's VoiceCallConsumer.
"""
import asyncio
import logging
import sys
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WebSocketEchoServer")

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8765


async def echo_handler(websocket, *args):
    """
    Handles an incoming WebSocket connection, echoing back every message
    prefixed with 'ECHO: '.
    """
    remote = getattr(websocket, "remote_address", "client")
    logger.info("Client connected: %s", remote)

    try:
        async for message in websocket:
            logger.info("Received from %s: %s", remote, message)
            # Echo back every message prefixed with "ECHO: "
            response = f"ECHO: {message}"
            await websocket.send(response)
            logger.info("Sent to %s: %s", remote, response)
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Client disconnected normally: %s", remote)
    except websockets.exceptions.ConnectionClosedError as exc:
        logger.warning("Client connection closed unexpectedly (%s): %s", remote, exc)
    except Exception as exc:
        logger.error("Error processing message from %s: %s", remote, exc)
    finally:
        logger.info("Connection terminated for: %s", remote)


async def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    logger.info("Starting WebSocket Echo Server on ws://%s:%d", host, port)
    async with websockets.serve(echo_handler, host, port):
        logger.info("WebSocket Echo Server is active and listening.")
        await asyncio.Future()  # Keep running


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    try:
        asyncio.run(main(host, port))
    except KeyboardInterrupt:
        logger.info("Server stopped by user interrupt.")
