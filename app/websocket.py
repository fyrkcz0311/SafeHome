"""Gestor de conexiones WebSocket para el dashboard en tiempo real."""

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """Envia un mensaje JSON a todos los clientes conectados."""
        muertos: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                muertos.append(ws)
        for ws in muertos:
            self.disconnect(ws)


manager = ConnectionManager()
