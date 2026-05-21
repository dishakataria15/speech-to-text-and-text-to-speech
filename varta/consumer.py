import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Conversation
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
        
        self.room_group_name = f'chat_{self.user.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        language = text_data_json.get('language', 'en')

        # Save message to database
        await self.save_message(self.user, message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'language': language
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        language = event['language']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'language': language
        }))

    @sync_to_async
    def save_message(self, user, message_text):
        Conversation.objects.create(user=user, message=message_text)