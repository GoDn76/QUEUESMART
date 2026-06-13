import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages active room-based WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        # Maps room IDs to sets of WebSocket connections
        self.counter_rooms: Dict[int, Set[WebSocket]] = {}
        self.display_board_rooms: Dict[int, Set[WebSocket]] = {}
        self.organization_rooms: Dict[int, Set[WebSocket]] = {}
        self.user_rooms: Dict[int, Set[WebSocket]] = {}

    # --- Connection Handlers ---

    async def connect_counter(self, counter_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.counter_rooms.setdefault(counter_id, set()).add(websocket)
        logger.info(f"WebSocket client connected to counter {counter_id} room. Total: {len(self.counter_rooms[counter_id])}")

    def disconnect_counter(self, counter_id: int, websocket: WebSocket) -> None:
        if counter_id in self.counter_rooms:
            self.counter_rooms[counter_id].discard(websocket)
            if not self.counter_rooms[counter_id]:
                del self.counter_rooms[counter_id]
            logger.info(f"WebSocket client disconnected from counter {counter_id} room.")

    async def connect_display(self, counter_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.display_board_rooms.setdefault(counter_id, set()).add(websocket)
        logger.info(f"WebSocket client connected to display board for counter {counter_id} room. Total: {len(self.display_board_rooms[counter_id])}")

    def disconnect_display(self, counter_id: int, websocket: WebSocket) -> None:
        if counter_id in self.display_board_rooms:
            self.display_board_rooms[counter_id].discard(websocket)
            if not self.display_board_rooms[counter_id]:
                del self.display_board_rooms[counter_id]
            logger.info(f"WebSocket client disconnected from display board for counter {counter_id} room.")

    async def connect_organization(self, organization_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.organization_rooms.setdefault(organization_id, set()).add(websocket)
        logger.info(f"WebSocket client connected to organization {organization_id} room. Total: {len(self.organization_rooms[organization_id])}")

    def disconnect_organization(self, organization_id: int, websocket: WebSocket) -> None:
        if organization_id in self.organization_rooms:
            self.organization_rooms[organization_id].discard(websocket)
            if not self.organization_rooms[organization_id]:
                del self.organization_rooms[organization_id]
            logger.info(f"WebSocket client disconnected from organization {organization_id} room.")

    async def connect_user(self, token_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.user_rooms.setdefault(token_id, set()).add(websocket)
        logger.info(f"WebSocket client connected to user {token_id} room. Total: {len(self.user_rooms[token_id])}")

    def disconnect_user(self, token_id: int, websocket: WebSocket) -> None:
        if token_id in self.user_rooms:
            self.user_rooms[token_id].discard(websocket)
            if not self.user_rooms[token_id]:
                del self.user_rooms[token_id]
            logger.info(f"WebSocket client disconnected from user {token_id} room.")

    # --- Broadcasting Core ---

    async def broadcast_to_counter(self, counter_id: int, message: Dict[str, Any]) -> None:
        """Send message to all websockets connected to the specific counter operator room."""
        sockets = self.counter_rooms.get(counter_id, set())
        if sockets:
            logger.debug(f"Broadcasting message to counter {counter_id} (count: {len(sockets)}): {message}")
            for socket in list(sockets):
                try:
                    await socket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to counter {counter_id}: {e}")
                    self.disconnect_counter(counter_id, socket)

    async def broadcast_to_display(self, counter_id: int, message: Dict[str, Any]) -> None:
        """Send message to all websockets connected to the specific counter display board room."""
        sockets = self.display_board_rooms.get(counter_id, set())
        if sockets:
            logger.debug(f"Broadcasting message to display board {counter_id} (count: {len(sockets)}): {message}")
            for socket in list(sockets):
                try:
                    await socket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to display board {counter_id}: {e}")
                    self.disconnect_display(counter_id, socket)

    async def broadcast_to_organization(self, organization_id: int, message: Dict[str, Any]) -> None:
        """Send message to all websockets connected to the organization room."""
        sockets = self.organization_rooms.get(organization_id, set())
        if sockets:
            logger.debug(f"Broadcasting message to organization {organization_id} (count: {len(sockets)}): {message}")
            for socket in list(sockets):
                try:
                    await socket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to organization {organization_id}: {e}")
                    self.disconnect_organization(organization_id, socket)

    async def broadcast_to_user(self, token_id: int, message: Dict[str, Any]) -> None:
        """Send targeted message to a specific user's websocket room."""
        sockets = self.user_rooms.get(token_id, set())
        if sockets:
            logger.debug(f"Broadcasting targeted message to user token {token_id} (count: {len(sockets)}): {message}")
            for socket in list(sockets):
                try:
                    await socket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to user token {token_id}: {e}")
                    self.disconnect_user(token_id, socket)

    # --- EventBus Integration Router ---

    async def start_event_bus_subscriptions(self, event_bus: Any) -> None:
        """Subscribe to EventBus patterns to routing events to appropriate local room connections."""
        logger.info("Initializing WebSocketManager EventBus subscriptions...")

        # 1. Route Counter events (e.g. TOKEN_CALLED, TOKEN_COMPLETED, TOKEN_SKIPPED, TOKEN_JOINED)
        async def handle_counter_event(msg: dict) -> None:
            counter_id = msg.get("counter_id")
            event_type = msg.get("event")
            if counter_id:
                # Both operators and display boards get these events
                await self.broadcast_to_counter(int(counter_id), msg)
                await self.broadcast_to_display(int(counter_id), msg)

            # Cleanup stale user connections when their token is finalized
            if event_type in ["TOKEN_COMPLETED", "TOKEN_SKIPPED"]:
                token_id = msg.get("token_id")
                if token_id and int(token_id) in self.user_rooms:
                    logger.info(f"Cleaning up user room for finalized token {token_id}")
                    for socket in list(self.user_rooms[int(token_id)]):
                        try:
                            await socket.close()
                        except Exception:
                            pass
                    self.user_rooms.pop(int(token_id), None)

        await event_bus.subscribe("counter:*", handle_counter_event)

        # 2. Route Organization events (e.g. general organization level metric updates)
        async def handle_org_event(msg: dict) -> None:
            org_id = msg.get("organization_id")
            if org_id:
                await self.broadcast_to_organization(int(org_id), msg)

        await event_bus.subscribe("organization:*", handle_org_event)

        # 3. Route User specific events (e.g. YOUR_TURN, TOKEN_NEAR)
        async def handle_user_event(msg: dict) -> None:
            token_id = msg.get("token_id")
            if token_id:
                await self.broadcast_to_user(int(token_id), msg)

        await event_bus.subscribe("user:*", handle_user_event)


# Global WebSocket Manager instance
websocket_manager = WebSocketManager()
