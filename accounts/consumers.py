import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardNotificationConsumer(AsyncWebsocketConsumer):
    """
    An asynchronous consumer that connects students to a real-time 
    notification stream on their dashboard.
    """
    async def connect(self):
        # Accept the incoming connection from the frontend dashboard
        await self.accept()
        
        # Send a welcoming handshake confirmation back to the client
        await self.send(text_data=json.dumps({
            "status": "connected",
            "message": "Welcome to Stephotec Real-Time System Services."
        }))

    async def disconnect(self, close_code):
        # Executed cleanly when the client leaves or closes the dashboard tab
        pass

    async def receive(self, text_data):
        # Triggered when the frontend pushes data to the backend via WebSocket
        data = json.loads(text_data)
        
        # Echo back the message for initial testing verification
        await self.send(text_data=json.dumps({
            "echo": data
        }))