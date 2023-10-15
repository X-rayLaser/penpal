from rest_framework import serializers
from .models import Chat, Message


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'prompt', 'human']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'text', 'date_time', 'generation_details', 'parent', 'replies', 'chat']
        read_only_fields = ['replies', 'chat']