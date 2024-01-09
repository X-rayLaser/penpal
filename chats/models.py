from django.db import models
from django.contrib.auth.models import User


class SystemMessage(models.Model):
    name = models.CharField(max_length=50)
    text = models.CharField(max_length=4096)

    created_time = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return self.name


class Chat(models.Model):
    system_message = models.OneToOneField(SystemMessage, related_name='chat', 
                                          blank=True, null=True, on_delete=models.SET_NULL)
    prompt = models.OneToOneField('Message', related_name='chat', on_delete=models.SET_NULL,
                                  blank=True, null=True)
    human = models.ForeignKey(User, related_name='chats', blank=True, null=True,
                              on_delete=models.CASCADE)


class Message(models.Model):
    text = models.CharField(max_length=4096)
    parent = models.ForeignKey('Message', related_name='replies', on_delete=models.CASCADE, 
                               blank=True, null=True)

    generation_details = models.JSONField(max_length=1024, blank=True, null=True)

    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    @property
    def human_produced(self):
        return self.generation_details is None

    @property
    def initial_prompt(self):
        message = self
        while message.parent:
            message = message.parent
        
        return message

    @property
    def siblings(self):
        if not self.parent:
            return []
        
        return self.parent.replies.all()
