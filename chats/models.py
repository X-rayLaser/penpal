from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from rest_framework.reverse import reverse


class SystemMessage(models.Model):
    name = models.CharField(max_length=50)
    text = models.CharField(max_length=4096)

    created_time = models.DateTimeField(auto_now_add=True, blank=True)
    user = models.ForeignKey(User, related_name='system_messages', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Preset(models.Model):
    name = models.CharField(max_length=50, unique=True)

    temperature = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    top_k = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )

    top_p = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )

    min_p = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )

    repeat_penalty = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    n_predict = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4096)]
    )

    user = models.ForeignKey(User, related_name='presets', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Configuration(models.Model):
    name = models.CharField(max_length=100)

    system_message = models.ForeignKey(SystemMessage, related_name="configurations",
                                       blank=True, null=True, on_delete=models.SET_NULL)
    preset = models.ForeignKey(Preset, related_name="configurations",
                               blank=True, null=True, on_delete=models.SET_NULL)

    tools = models.JSONField()

    template_spec = models.JSONField(blank=True, null=True)

    voice_id = models.CharField(max_length=500, blank=True, null=True)

    sandboxes = models.JSONField(blank=True, null=True)

    user = models.ForeignKey(User, related_name='configurations', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Chat(models.Model):
    configuration = models.ForeignKey(Configuration, related_name='chats',
                                      blank=True, null=True, on_delete=models.SET_NULL)
    system_message = models.CharField(max_length=4096, blank=True, null=True)

    prompt = models.OneToOneField('Message', related_name='chat', on_delete=models.SET_NULL,
                                  blank=True, null=True)
    user = models.ForeignKey(User, related_name='chats', on_delete=models.CASCADE)

    date_time = models.DateTimeField(auto_now_add=True, blank=True)


class Message(models.Model):
    text = models.CharField(max_length=8000)
    parent = models.ForeignKey('Message', related_name='replies', on_delete=models.CASCADE, 
                               blank=True, null=True)

    generation_details = models.JSONField(max_length=1024, blank=True, null=True)

    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    audio = models.FileField(upload_to="uploads/audio", blank=True, null=True)

    image = models.ImageField(upload_to="uploads/chat_images", blank=True, null=True)

    attachments_text = models.TextField(max_length=100000, blank=True, null=True)

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

    def get_chat(self):
        return self._get_chat(msg=self)

    def _get_chat(self, msg):
        try:
            return msg.chat
        except Message.chat.RelatedObjectDoesNotExist:
            return self._get_chat(msg.parent)


class Attachment(models.Model):
    original_name = models.CharField(max_length=512)
    file = models.FileField(upload_to="uploads/attachments")

    message = models.ForeignKey(Message, related_name='attachments', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.original_name


class SpeechSample(models.Model):
    text = models.CharField(max_length=1024)
    audio = models.FileField(upload_to="uploads/audio")
    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self) -> str:
        return self.text

    def get_absolute_url(self):
        return reverse('speechsample-detail', args=[self.pk])
