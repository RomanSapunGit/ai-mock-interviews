from uuid import UUID
from fastapi import APIRouter, WebSocket
from app.sessions.ws import handle_session_ws

router = APIRouter()

@router.websocket("/{session_id}/ws")
async def session_websocket(session_id: UUID, websocket: WebSocket):
    await handle_session_ws(websocket, session_id)
