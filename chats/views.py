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
from rest_framework import viewsets, generics, views
from rest_framework.parsers import BaseParser
from rest_framework.decorators import parser_classes
from rest_framework.renderers import BaseRenderer

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


class PresetViewSet(viewsets.ModelViewSet):
    serializer_class = PresetSerializer
    queryset = Preset.objects.all()


class ConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = ConfigurationSerializer
    queryset = Configuration.objects.all()


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
def generate_reply(request):
    return _generate_completion(request)


class BinaryParser(BaseParser):
    """Binary data parser"""
    media_type = 'application/octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


@api_view(["POST"])
@parser_classes([BinaryParser])
def transcribe_speech(request):
    raw_audio = request.data
    text = stt_backend(raw_audio)
    return Response({"text": text})


class ChatList(generics.ListCreateAPIView):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    pagination_class = DefaultPagination


@api_view(['GET', 'PATCH', 'DELETE'])
def chat_detail(request, pk):
    try:
        chat = Chat.objects.get(pk=pk)
    except Chat.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ChatSerializer(chat)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    if request.method == 'PATCH':
        serializer = ChatSerializer(chat, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    if request.method == 'DELETE':
        chat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def treebank_detail(request, pk):
    try:
        chat = Chat.objects.get(pk=pk)
    except Chat.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not chat.prompt:
        return Response({}, status=status.HTTP_200_OK)

    serializer = TreebankSerializer(chat.prompt)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def message_list(request):
    if request.method == 'GET':
        messages = Message.objects.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    data = request.data.copy()

    if 'image_data_uri' in data:
        image_b64 = data.pop('image_data_uri')[0]
        fmt, image_str = image_b64.split(';base64,')
        extension = fmt.split('/')[-1]

        image_data = base64.b64decode(image_str)

        extension = extension or imghdr.what(None, h=image_data) or "jpg"
        image = ContentFile(image_data, name=f'prompt_image.{extension}')
    else:
        image = None

    data['image'] = image
    serializer = MessageSerializer(data=data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
