import re
import base64
import os
import markdown
import bleach
from rest_framework import serializers
from .models import SystemMessage, Preset, Configuration, Chat, Message, Attachment, SpeechSample
from tools.api_calls import backend


class SpeechSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechSample
        fields = ['id', 'text', 'audio']


class SystemMessageSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = SystemMessage
        fields = ['id', 'name', 'text', 'user']


class PresetSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    class Meta:
        model = Preset
        fields = ['id', 'name', 'temperature', 'top_k', 
                  'top_p', 'min_p', 'repeat_penalty', 'n_predict', 'user']


class ConfigurationSerializer(serializers.ModelSerializer):
    system_message_ro = SystemMessageSerializer(source="system_message", read_only=True)
    preset_ro = PresetSerializer(source="preset", read_only=True)
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Configuration
        fields = ['id', 'name', 'model_repo',
                  'file_name', 'launch_params', 'system_message',
                  'system_message_ro', 'preset', 'preset_ro', 
                  'tools', 'template_spec', 'voice_id', 'user']

    def update(self, instance, validated_data):
        # todo: consider other approaches
        self.pop_if_exists(validated_data, 'system_message')
        self.pop_if_exists(validated_data, 'preset')
        self.pop_if_exists(validated_data, 'tools')

        return super().update(instance, validated_data)

    def pop_if_exists(self, validated_data, field):
        if field in validated_data:
            validated_data.pop(field)


class ChatSerializer(serializers.ModelSerializer):
    prompt_text = serializers.ReadOnlyField(source='prompt.text', default="**No data yet**")
    configuration_ro = ConfigurationSerializer(source="configuration", read_only=True)
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Chat
        fields = ['id', 'configuration', 'configuration_ro', 'system_message',
                  'prompt_text', 'user', 'date_time']
        extra_kwargs = {'configuration': dict(required=True)}

    def update(self, instance, validated_data):
        # todo: consider other approaches
        if 'configuration' in validated_data:
            validated_data.pop('configuration')
        return super().update(instance, validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'original_name', 'file', 'message']
        read_only_fields = ['original_name', 'file', 'message']


class MessageSerializer(serializers.ModelSerializer):
    chat = serializers.PrimaryKeyRelatedField(many=False, required=False, queryset=Chat.objects.all())

    clean_text = serializers.SerializerMethodField()
    html = serializers.SerializerMethodField()
    image_b64 = serializers.SerializerMethodField()
    attachments = serializers.ListField(
        child=serializers.FileField(max_length=None, allow_empty_file=True),
        allow_empty=True, min_length=None, max_length=None, write_only=True, required=False)

    relative_paths = serializers.JSONField(required=False, write_only=True)

    attached_files = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'text', 'clean_text', 'html', 'date_time',
                  'generation_details', 'parent', 'replies', 'chat',
                  'audio', 'image', 'image_b64', 'attachments', 'attached_files', 'relative_paths']
        read_only_fields = ['replies', 'audio']

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

    def get_attached_files(self, obj):
        return [attachment.original_name for attachment in obj.attachments.all()]

    def get_image_b64(self, obj):
        return to_data_uri(obj.image)

    def create(self, validated_data):
        attachments = []
        if 'attachments' in validated_data:
            attachments = validated_data.pop('attachments')

        relative_paths = {}
        if 'relative_paths' in validated_data:
            # todo: do extra validation of path
            relative_paths = validated_data.pop('relative_paths')

        obj = super().create(validated_data)

        if attachments:
            for attach in attachments:
                file_path = self.obtain_file_path(relative_paths, attach)
                Attachment.objects.create(original_name=file_path, file=attach, message=obj)

        if "chat" in validated_data:
            obj.chat = validated_data["chat"]
            obj.save()
            obj.chat.save()
        return obj

    def obtain_file_path(self, paths, attached_file):
        try:
            file_path = paths[attached_file.name]['path']
        except KeyError:
            file_path = attached_file.name

        return file_path


class TreebankSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    image_b64 = serializers.SerializerMethodField()
    attached_files = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'text', 'date_time', 'generation_details', 'parent',
                  'replies', 'chat', 'image', 'image_b64', 'attached_files']
        read_only_fields = ['replies', 'chat']

    def get_replies(self, obj):
        res = []
        for reply in obj.replies.all():
            item = MessageSerializer(instance=reply).data
            item['replies'] = self.get_replies(reply)
            res.append(item)
    
        return res

    def get_image_b64(self, obj):
        return to_data_uri(obj.image)

    def get_attached_files(self, obj):
        return [attachment.original_name for attachment in obj.attachments.all()]


def to_data_uri(image):
    if not image:
        return None

    with open(image.path, "rb") as f:
        data = f.read()

    _, extension = os.path.splitext(image.path)
    extension = extension[1:]
    image_b64_string = base64.b64encode(data).decode('utf-8')
    return f"data:image/{extension};base64,{image_b64_string}"