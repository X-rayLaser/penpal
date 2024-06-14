import json
import os
import wave
import uuid
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets, generics
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


def _generate_completion(request):
    body = request.data
    prompt = body.get("prompt")
    inference_config = body.get("inference_config")
    llm_settings = body.get("llm_settings", {})
    clear_context = body.get("clear_context", False)
    socket_session_id = body.get("socketSessionId")

    if prompt:
        print("about to start streaming. Prompt:", prompt)
        task = generate_llm_response.delay(prompt, inference_config, clear_context, llm_settings, socket_session_id)
        return Response({'task_id': task.task_id})

    return Response({'errors': ["Expected 'prompt' field in json request body"]}, 
                    status=status.HTTP_400_BAD_REQUEST)


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


def join_wavs(samples, result_path):
    data= []
    params = None

    for sample in samples:
        file_field = sample.audio
        w = wave.open(file_field.path, 'rb')
        params = w.getparams()
        data.append(w.readframes(w.getnframes()))
        w.close()

    with wave.open(result_path, 'wb') as output:
        output.setparams(params)
        for row in data:
            output.writeframes(row)

    with open(result_path, 'rb') as f:
        res = f.read()
    
    os.remove(result_path)
    return res


@api_view(["POST"])
def generate_speech(request, message_pk):
    # todo: move this heavy logic to a separate celery task
    message = get_object_or_404(Message, pk=message_pk)

    sample_ids = request.data["samples"]

    wav_files = SpeechSample.objects.filter(id__in=sample_ids)

    if wav_files:
        output_name = f'{uuid.uuid4().hex}.wav'
        output_path = os.path.join(settings.MEDIA_ROOT, output_name)
        audio_data = join_wavs(wav_files, output_path)

        audio_file = ContentFile(audio_data, name="tts-audio-file.wav")
        message.audio = audio_file
        message.save()
    
    ser = MessageSerializer(message, context={'request': request})
    return Response(ser.data, status=status.HTTP_200_OK)


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
    
    serializer = MessageSerializer(data=request.data)
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
