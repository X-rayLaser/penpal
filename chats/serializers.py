from rest_framework import serializers
from .models import SystemMessage, Preset, Chat, Message
import markdown


class SystemMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMessage
        fields = ['id', 'name', 'text']


class PresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preset
        fields = ['id', 'name', 'temperature', 'top_k', 
                  'top_p', 'min_p', 'repeat_penalty', 'n_predict']


class ChatSerializer(serializers.ModelSerializer):
    prompt_text = serializers.ReadOnlyField(source='prompt.text', default="**No data yet**")

    system_message_ro = SystemMessageSerializer(source="system_message", read_only=True)

    class Meta:
        model = Chat
        fields = ['id', 'system_message', 'system_message_ro', 'prompt_text', 'human']

    def update(self, instance, validated_data):
        # todo: consider other approaches
        validated_data.pop('system_message')
        return super().update(instance, validated_data)


class MessageSerializer(serializers.ModelSerializer):
    chat = serializers.PrimaryKeyRelatedField(many=False, required=False, queryset=Chat.objects.all())
    html = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'text', 'html', 'date_time', 'generation_details', 'parent', 'replies', 'chat']
        read_only_fields = ['replies']

    def get_html(self, obj):
        return markdown.markdown(obj.text, extensions=['fenced_code'])

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
