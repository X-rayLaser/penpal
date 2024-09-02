import json
import os
import wave
import uuid
import base64
import re
import imghdr
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets, generics, mixins, views
from rest_framework.parsers import BaseParser
from rest_framework.decorators import parser_classes, permission_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.http.response import StreamingHttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from django.conf import settings

from .models import SystemMessage, Preset, Configuration, Chat, Message, SpeechSample
from .serializers import (
    ChatSerializer,
    ConfigurationSerializer,
    PresetSerializer,
    MessageSerializer,
    TreebankSerializer,
    SystemMessageSerializer,
    SpeechSampleSerializer
)
from chats import permissions
from .utils import join_wavs


import llm_utils
from tools import llm_tools, get_specification
from tools.api_calls import (
    find_api_call,
    make_api_call,
    ApiFunctionCall,
    ApiCallNotFoundError
)
from tts import tts_backend
from stt import stt_backend
from .pagination import DefaultPagination
from .tasks import generate_llm_response


class BinaryRenderer(BaseRenderer):
    media_type = 'application/octet-stream'
    format = 'bin'
    render_style = 'binary'
    charset = None

    def render(self, data, media_type=None, renderer_context=None):
        view = renderer_context['view']

        with open(view.get_object().audio.path, 'rb') as f:
            return f.read()


class AudioVerbatimRenderer(BinaryRenderer):
    media_type = 'audio/*'

    def render(self, data, media_type=None, renderer_context=None):
        return data


class SystemMessageViewSet(viewsets.ModelViewSet):
    serializer_class = SystemMessageSerializer
    queryset = SystemMessage.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return SystemMessage.objects.filter(user=self.request.user)


class PresetViewSet(viewsets.ModelViewSet):
    serializer_class = PresetSerializer
    queryset = Preset.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Preset.objects.filter(user=self.request.user)


class ConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = ConfigurationSerializer
    queryset = Configuration.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsOwner]


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Configuration.objects.filter(user=self.request.user)


class SpeechSampleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SpeechSampleSerializer
    queryset = SpeechSample.objects.all()
    renderer_classes = [BinaryRenderer]

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class VoiceSampleView(views.APIView):
    renderer_classes = [AudioVerbatimRenderer]

    def get(self, request):
        voice_id = request.query_params['voice_id']
        content = tts_backend.get_voice_sample(voice_id)
        return Response(content)


def _generate_completion(request):
    body = request.data
    inference_config = body.get("inference_config")
    llm_settings = body.get("llm_settings", {})
    clear_context = body.get("clear_context", False)
    socket_session_id = body.get("socketSessionId")
    image_b64 = body.get("image_data_uri")
    voice_id = body.get("voice_id")

    parent_message_id = int(body.get("parent", -1))

    image_data = base64.b64decode(image_b64) if image_b64 else None
        
    spec = llm_utils.GenerationSpec(
        prompt="",
        inference_config=inference_config,
        sampling_config=llm_settings,
        clear_context=clear_context,
        image_b64=image_data,
        parent_message_id=parent_message_id,
        voice_id=voice_id
    )

    celery_task = generate_llm_response.delay(spec.to_dict(), socket_session_id)
    return Response({'task_id': celery_task.task_id})


@api_view(["POST"])
def generate_completion(request):
    return _generate_completion(request)


@csrf_exempt
def clear_llm_context(request):
    if request.method == 'POST':
        llm_utils.clear_context()
        return Response({})
    
    return HttpResponseNotAllowed(["POST"])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_reply(request):
    return _generate_completion(request)


class BinaryParser(BaseParser):
    """Binary data parser"""
    media_type = 'application/octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


@api_view(["POST"])
@parser_classes([BinaryParser])
@permission_classes([IsAuthenticated])
def transcribe_speech(request):
    raw_audio = request.data
    text = stt_backend(raw_audio)
    return Response({"text": text})


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    pagination_class = DefaultPagination
    permission_classes = [IsAuthenticated, permissions.IsOwner]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options', 'trace']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)


class TreeBankDetailView(generics.RetrieveAPIView):
    queryset = Chat.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsOwner]

    def get_serializer(self, *args, **kwargs):
        chat = self.get_object()
        return TreebankSerializer(chat.prompt)

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        if not self.get_object().prompt:
            return Response({}, status=status.HTTP_200_OK)
        return super().retrieve(request, *args, **kwargs)


class MessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer(self, *args, **kwargs):
        data = self.request.data.copy()
        data['image'] = self._get_image(data)
        return MessageSerializer(data=data)

    def perform_create(self, serializer):
        chat_id = self.request.data.get("chat")
        if chat_id:
            chat = generics.get_object_or_404(Chat.objects.all(), pk=chat_id)
        else:
            parent_id = self.request.data.get("parent")
            parent = generics.get_object_or_404(Message.objects.all(), pk=parent_id)
            chat = parent.get_chat()

        user_owns_parent = (self.request.user and self.request.user == chat.user)
        if not user_owns_parent:
            raise PermissionDenied("Only chat owners can add messages to their chats")

        return super().perform_create(serializer)

    def _get_image(self, data):
        if 'image_data_uri' not in data:
            if 'image' in data:
                return data['image']
            return None

        data_uri = data.pop('image_data_uri')[0]
        image_data, extension = decode_data_image(data_uri)
        return ContentFile(image_data, name=f'prompt_image.{extension}')


def decode_data_image(data_uri):
    fmt, image_str = data_uri.split(';base64,')
    extension = fmt.split('/')[-1]

    image_data = base64.b64decode(image_str)

    extension = extension or imghdr.what(None, h=image_data) or "jpg"
    return image_data, extension


# todo: consider to delete the view
@api_view(['GET', 'DELETE'])
def message_detail(request, pk):
    try:
        message = Message.objects.get(pk=pk)
    except Message.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    if request.method == 'DELETE':
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['get'])
def supported_tools(request):
    tools = [tool.lower() for tool in llm_tools.keys()]
    return Response(tools)


@api_view(['get'])
@permission_classes([IsAuthenticated])
def list_voices(request):
    voices = tts_backend.list_voices()
    return Response(voices)


@api_view(['GET'])
def tools_specification(request):
    conf_id = request.query_params.get('conf_id')
    configuration = Configuration.objects.get(pk=conf_id)

    full_spec = get_specification(configuration)
    print('full spec:\n', full_spec)
    return Response({ 'spec': full_spec })


# todo: delete it
@api_view(['GET'])
def find_api_call_view(request):
    text = request.query_params.get('text')

    try:
        api_call, offset = find_api_call(text)
        res = {
            'offset': offset,
            'api_call': api_call.todict()
        }
    except ApiCallNotFoundError:
        res = {}

    return Response(res)


# todo: delete it
@api_view(['GET'])
def call_api_view(request):
    name = request.query_params.get('name')
    arg_string = request.query_params.get('arg_string')


    print('query params', request.query_params, 'tool', name, 'arg string', arg_string, 'llm_tools', llm_tools)
    args = arg_string.split(",")
    args = [arg.strip().lower() for arg in args]

    api_call = ApiFunctionCall(name, args)
    api_call_string = make_api_call(api_call)

    print('api_call_string', api_call_string)

    return Response({
        'api_call_string': api_call_string
    })
