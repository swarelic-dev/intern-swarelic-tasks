"""
server.py — Exercise 4.3: WebSocket Echo Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Accepts WebSocket connections and echoes every message back prefixed with "ECHO: ".

Usage
-----
    # Install dependency (one-time)
    pip install websockets

    # Run the server
    python server.py

The server listens on ws://localhost:8765
Open client.html in a browser to interact with it.
"""

import asyncio
import websockets
from websockets.server import WebSocketServerProtocol


async def echo_handler(websocket: WebSocketServerProtocol) -> None:
    """
    Handle a single WebSocket connection.

    Listens for incoming messages and echoes each one back to the same
    client, prefixed with "ECHO: ".

    This mirrors the pattern used in SCAI's VoiceCallConsumer, where the
    server maintains a persistent, bidirectional connection with a client
    and processes each message as it arrives.
    """
    client_addr = websocket.remote_address
    print(f"[+] Client connected:    {client_addr}")

    try:
        async for message in websocket:
            print(f"[→] Received from {client_addr}: {message}")
            response = f"ECHO: {message}"
            await websocket.send(response)
            print(f"[←] Sent to     {client_addr}: {response}")

    except websockets.exceptions.ConnectionClosedOK:
        pass  # clean disconnect — nothing to do
    except websockets.exceptions.ConnectionClosedError as exc:
        print(f"[!] Connection closed with error: {exc}")
    finally:
        print(f"[-] Client disconnected: {client_addr}")


async def main() -> None:
    host, port = "localhost", 8765
    print(f"WebSocket Echo Server running on ws://{host}:{port}")
    print("Open client.html in your browser to connect.\n")

    async with websockets.serve(echo_handler, host, port):
        await asyncio.Future()   # keep running forever


if __name__ == "__main__":
    asyncio.run(main())
