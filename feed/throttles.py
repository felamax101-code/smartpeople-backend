
from rest_framework.throttling import ScopedRateThrottle

class VideoStatusThrottle(ScopedRateThrottle):
    scope = "video_status"
