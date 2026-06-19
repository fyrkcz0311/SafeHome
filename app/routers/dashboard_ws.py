"""WebSocket del dashboard en tiempo real."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket import manager

router = APIRouter(tags=["tiempo-real"])


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"tipo": "conectado", "mensaje": "Dashboard en linea"})
        while True:
            # Mantiene la conexion viva; ignora lo que envie el cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
