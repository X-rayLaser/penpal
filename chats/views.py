import json
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from django.http.response import StreamingHttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import SystemMessage, Preset, Configuration, Chat, Message
from .serializers import (
    ChatSerializer,
    ConfigurationSerializer,
    PresetSerializer,
    MessageSerializer,
    TreebankSerializer,
    SystemMessageSerializer
)
import llm_utils
from tools import llm_tools, get_specification
from tools.api_calls import (
    find_api_call,
    make_api_call,
    ApiFunctionCall,
    ApiCallNotFoundError
)


class SystemMessageViewSet(viewsets.ModelViewSet):
    serializer_class = SystemMessageSerializer
    queryset = SystemMessage.objects.all()


class PresetViewSet(viewsets.ModelViewSet):
    serializer_class = PresetSerializer
    queryset = Preset.objects.all()


class ConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = ConfigurationSerializer
    queryset = Configuration.objects.all()


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
