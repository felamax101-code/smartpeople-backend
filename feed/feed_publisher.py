import redis
import json
import uuid
from decimal import Decimal
from django.conf import settings

_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

FEED_CHANNEL = "feed:global"
class FeedEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def publish_new_feed_event(event_type: str, data: dict):
    try:
        
        _redis.publish(FEED_CHANNEL, json.dumps({
            "type": event_type,
            "data": data
        }, cls=FeedEncoder))  # use custom encoder
    except Exception as e:
        print(f"[feed_publisher] Redis publish failed: {e}")
        
        
def publish_update_feed_event(event_type: str, data: dict):
    try:
        
        _redis.publish(FEED_CHANNEL, json.dumps({
            "type": event_type,
            "data": data
        }, cls=FeedEncoder))  # use custom encoder
    except Exception as e:
        print(f"[feed_publisher] Redis publish failed: {e}")
        
        
        
        
def publish_feed_event(event_type: str, data: dict):
    try:
        
        _redis.publish(FEED_CHANNEL, json.dumps({
            "type": event_type,
            "data": data
        }, cls=FeedEncoder))  # use custom encoder
    except Exception as e:
        print(f"[feed_publisher] Redis publish failed: {e}")