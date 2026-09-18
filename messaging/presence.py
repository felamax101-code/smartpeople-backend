# messaging/presence.py
from django.core.cache import cache

HEARTBEAT_INTERVAL = 25
PRESENCE_TTL = 35
TYPING_TTL = 5


def presence_key(user_id):
    return f"presence:{user_id}"


def typing_key(conversation_id, user_id):
    return f"typing:{conversation_id}:{user_id}"


def set_online(user_id):
    cache.set(presence_key(user_id), True, timeout=PRESENCE_TTL)


def refresh_presence(user_id):
    cache.set(presence_key(user_id), True, timeout=PRESENCE_TTL)


def set_offline(user_id):
    cache.delete(presence_key(user_id))


def is_online(user_id):
    return cache.get(presence_key(user_id)) is not None


def set_typing(conversation_id, user_id):
    cache.set(typing_key(conversation_id, user_id), True, timeout=TYPING_TTL)


def clear_typing(conversation_id, user_id):
    cache.delete(typing_key(conversation_id, user_id))