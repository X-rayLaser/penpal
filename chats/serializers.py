import re
import markdown
from rest_framework import serializers
from .models import SystemMessage, Preset, Configuration, Chat, Message
from tools.api_calls import backend


class SystemMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMessage
        fields = ['id', 'name', 'text']


class PresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preset
        fields = ['id', 'name', 'temperature', 'top_k', 
                  'top_p', 'min_p', 'repeat_penalty', 'n_predict']


class ConfigurationSerializer(serializers.ModelSerializer):

    system_message_ro = SystemMessageSerializer(source="system_message", read_only=True)
    preset_ro = PresetSerializer(source="preset", read_only=True)

    class Meta:
        model = Configuration
        fields = ['id', 'name', 'context_size', 'system_message',
                  'system_message_ro', 'preset', 'preset_ro', 'tools']

    def update(self, instance, validated_data):
        # todo: consider other approaches
        validated_data.pop('system_message')
        validated_data.pop('preset')
        validated_data.pop('tools')
        return super().update(instance, validated_data)


class ChatSerializer(serializers.ModelSerializer):
    prompt_text = serializers.ReadOnlyField(source='prompt.text', default="**No data yet**")

    system_message_ro = SystemMessageSerializer(source="system_message", read_only=True)

    configuration_ro = ConfigurationSerializer(source="configuration", read_only=True)

    class Meta:
        model = Chat
        fields = ['id', 'configuration', 'configuration_ro', 'system_message',
                  'system_message_ro', 'prompt_text', 'human', 'date_time']

    def update(self, instance, validated_data):
        # todo: consider other approaches
        validated_data.pop('system_message')
        validated_data.pop('configuration')
        return super().update(instance, validated_data)


class MessageSerializer(serializers.ModelSerializer):
    chat = serializers.PrimaryKeyRelatedField(many=False, required=False, queryset=Chat.objects.all())
    html = serializers.SerializerMethodField()
    clean_text = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'text', 'clean_text', 'html', 'date_time',
                  'generation_details', 'parent', 'replies', 'chat']
        read_only_fields = ['replies']

    def get_clean_text(self, obj):
        open_tag = backend.open_apicall_tag
        tags_to_remove = [(backend.get_apicall_open_tag(), backend.get_apicall_close_tag()),
                          (backend.get_result_open_tag(), backend.get_result_close_tag()),
                          (backend.get_error_open_tag(), backend.get_error_close_tag())]

        output = obj.text
        for open_tag, close_tag in tags_to_remove:
            pattern = re.compile(f'{open_tag}.*{close_tag}')
            output = pattern.sub("", output)
            output = output.replace(open_tag, "").replace(close_tag, "")
        
        return output

    def get_html(self, obj):
        return markdown.markdown(self.get_clean_text(obj), extensions=['fenced_code'])

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
