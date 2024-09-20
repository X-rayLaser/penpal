from chats import models


def default_preset_data():
    return {
        'name': 'default',
        'temperature': 0.1,
        'top_k': 40,
        'top_p': 0.95,
        'min_p': 0.05,
        'repeat_penalty': 1.1,
        'n_predict': 512
    }


def default_system_msg_data():
    return {
        "name": "assistant",
        "text": "You are a helpful assistant"
    }


def default_configuration_data(user):
    preset = models.Preset.objects.create(user=user, **default_preset_data())
    system_msg = models.SystemMessage.objects.create(user=user, **default_system_msg_data())

    return {
        'user': user,
        'name': 'myconf',
        'system_message': system_msg,
        'preset': preset,
        'tools': [],
        'sandboxes': {}
    }