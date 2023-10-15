from django.http.response import HttpResponse
from django.shortcuts import render


def index(request):
    context = {}
    return render(request, "chats/index.html", context)
