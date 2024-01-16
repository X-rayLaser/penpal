import json
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from django.http.response import StreamingHttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import SystemMessage, Preset, Chat, Message
from .serializers import (
    ChatSerializer,
    PresetSerializer,
    MessageSerializer,
    TreebankSerializer,
    SystemMessageSerializer
)
import llm_utils
from plugins import llm_tools


class SystemMessageViewSet(viewsets.ModelViewSet):
    serializer_class = SystemMessageSerializer
    queryset = SystemMessage.objects.all()


class PresetViewSet(viewsets.ModelViewSet):
    serializer_class = PresetSerializer
    queryset = Preset.objects.all()


@csrf_exempt
def generate_completion(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        prompt = body.get("prompt")
        llm_settings = body.get("llm_settings", {})
        clear_context = body.get("clear_context", False)

        if prompt:
            print("about to start streaming. Prompt:", prompt)
            response = StreamingHttpResponse(
                llm_utils.stream_tokens(prompt, clear_context, llm_settings)
            )
            return response
        return HttpResponseBadRequest("Expected 'prompt' field in json request body")
    
    return HttpResponseNotAllowed(["POST"])


@csrf_exempt
def clear_llm_context(request):
    if request.method == 'POST':
        llm_utils.clear_context()
        return Response({})
    
    return HttpResponseNotAllowed(["POST"])


@csrf_exempt
def generate_reply(request):
    return generate_completion(request)


@api_view(['GET', 'POST'])
def chat_list(request):
    if request.method == 'GET':
        chats = Chat.objects.all()
        serializer = ChatSerializer(chats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    serializer = ChatSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def chat_detail(request, pk):
    try:
        chat = Chat.objects.get(pk=pk)
    except Chat.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ChatSerializer(chat)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
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


@api_view(['GET'])
def call_api(request):
    tool = request.query_params.get('tool')
    arg_string = request.query_params.get('arg_string')
    print('tool', tool, 'arg string', arg_string)
    args = arg_string.split(",")
    args = [arg.strip().lower() for arg in args]

    func = llm_tools.get(tool)
    if not func:
        Response({tool: 'This tool does not exist'}, status=400)
    
    print('tool', tool, 'args', args)
    try:
        result = func(*args)
        data = dict(result=result)
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({ tool: f'Invalid tool use: {repr(e)}' }, status=status.HTTP_400_BAD_REQUEST)
