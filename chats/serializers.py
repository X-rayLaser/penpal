from rest_framework import serializers
from .models import Chat, Message


class ChatSerializer(serializers.ModelSerializer):
    prompt_text = serializers.ReadOnlyField(source='prompt.text', default="**No data yet**")
    class Meta:
        model = Chat
        fields = ['id', 'prompt_text', 'human']


class MessageSerializer(serializers.ModelSerializer):
    chat = serializers.PrimaryKeyRelatedField(many=False, required=False, queryset=Chat.objects.all())
    class Meta:
        model = Message
        fields = ['id', 'text', 'date_time', 'generation_details', 'parent', 'replies', 'chat']
        read_only_fields = ['replies']

    def create(self, validated_data):
        print(validated_data)
        obj = super().create(validated_data)

        if "chat" in validated_data:
            obj.chat = validated_data["chat"]
            obj.save()
            obj.chat.save()
        return obj


class TreebankSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'text', 'date_time', 'generation_details', 'parent', 'replies', 'chat']
        read_only_fields = ['replies', 'chat']

    def get_replies(self, obj):
        res = []
        for reply in obj.replies.all():
            item = MessageSerializer(instance=reply).data
            item['replies'] = self.get_replies(reply)
            res.append(item)
    
        return res
