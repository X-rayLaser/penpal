from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from rest_framework.reverse import reverse


class SystemMessage(models.Model):
    name = models.CharField(max_length=50)
    text = models.CharField(max_length=4096)

    created_time = models.DateTimeField(auto_now_add=True, blank=True)

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

    def __str__(self):
        return self.name


class Configuration(models.Model):
    name = models.CharField(max_length=100)

    model_repo = models.CharField(max_length=256)

    file_name = models.CharField(max_length=256)

    #depreacated
    context_size = models.PositiveIntegerField(
        default=512, validators=[MinValueValidator(1), MaxValueValidator(100000)]
    )

    launch_params = models.JSONField()

    system_message = models.ForeignKey(SystemMessage, related_name="configurations",
                                       blank=True, null=True, on_delete=models.SET_NULL)
    preset = models.ForeignKey(Preset, related_name="configurations",
                               blank=True, null=True, on_delete=models.SET_NULL)

    tools = models.JSONField()

    template_spec = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class Chat(models.Model):
    configuration = models.ForeignKey(Configuration, related_name='chats',
                                      blank=True, null=True, on_delete=models.SET_NULL)
    system_message = models.ForeignKey(SystemMessage, related_name='chats',
                                       blank=True, null=True, on_delete=models.SET_NULL)
    prompt = models.OneToOneField('Message', related_name='chat', on_delete=models.SET_NULL,
                                  blank=True, null=True)
    human = models.ForeignKey(User, related_name='chats', blank=True, null=True,
                              on_delete=models.CASCADE)

    date_time = models.DateTimeField(auto_now_add=True, blank=True)


class Message(models.Model):
    text = models.CharField(max_length=4096)
    parent = models.ForeignKey('Message', related_name='replies', on_delete=models.CASCADE, 
                               blank=True, null=True)

    generation_details = models.JSONField(max_length=1024, blank=True, null=True)

    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    audio = models.FileField(upload_to="uploads/audio", blank=True, null=True)

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


class SpeechSample(models.Model):
    text = models.CharField(max_length=1024)
    audio = models.FileField(upload_to="uploads/audio")
    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self) -> str:
        return self.text

    def get_absolute_url(self):
        return reverse('speechsample-detail', args=[self.pk])
