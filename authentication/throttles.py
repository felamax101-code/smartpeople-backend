

import time
import logging
from django.core.cache import caches, InvalidCacheBackendError
from rest_framework.throttling import BaseThrottle
from rest_framework.exceptions import Throttled
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)


#  Cache helper 

def _get_cache():
    """
    Try Redis first ('default' cache, expected to be django-redis in prod).
    Falls back to Django's local memory cache if Redis is unavailable.
    This means throttling still works in dev and during Redis outages —
    just not shared across workers.
    """
    try:
        cache = caches['default']
        cache.get('__throttle_ping__')  # probe the connection
        return cache
    except (InvalidCacheBackendError, Exception):
        logger.warning("Throttle: Redis unavailable, falling back to local memory cache.")
        return caches['locmem']


#  Base progressive throttle 

class ProgressiveThrottle(BaseThrottle):
    """
    Base class. Subclasses define:
        scope          — used in cache key prefix
        stages         — list of (max_attempts, window_seconds, retry_after_seconds)
                         evaluated in order; first matching stage is applied
        cache_ttl      — how long to keep the history in cache (seconds)

    Stages :
        (5, 60, 0)     — up to 5 attempts per 60s window, no extra penalty
        (10, 300, 30)  — up to 10 attempts per 5min window, wait 30s if exceeded
        (20, 3600, 300) — up to 20 attempts per hour, wait 5min if exceeded
        (None, 86400, 3600) — catch-all: after all above, lock for 1 hour

    None as max_attempts means "you've exhausted all stages — full lockout."
    """

    scope = 'base'
    cache_ttl = 86400  # keep history for 24h

    # Override in subclasses
    stages = [
        (5,    60,    0),       # stage 1: 5/min — normal
        (10,   300,   30),      # stage 2: 10/5min — slow down
        (20,   3600,  300),     # stage 3: 20/hr — heavily slowed
        (None, 86400, 3600),    # stage 4: lockout for 1h
    ]

    def get_ident(self, request):
        """IP address of the requester, respecting proxies."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def get_identifier_from_body(self, request):
        """
        Override in subclasses to extract email/username from request body.
        Returns None if not applicable.
        """
        return None

    def build_cache_keys(self, request):
        """
        Returns a list of cache keys to check and update.
        Always includes IP. Adds identifier key if extractable.
        Combined key (IP+identifier) catches credential stuffing
        while individual keys catch distributed attacks.
        """
        ip = self.get_ident(request)
        keys = [f'throttle:{self.scope}:ip:{ip}']

        identifier = self.get_identifier_from_body(request)
        if identifier :
            clean = identifier.lower().strip()
            keys.append(f'throttle:{self.scope}:id:{clean}')
            keys.append(f'throttle:{self.scope}:combined:{ip}:{clean}')

        return keys

    def _get_history(self, cache, key):
        try:
            return cache.get(key) or []
        except Exception:
            return []

    def _set_history(self, cache, key, history):
        try:
            cache.set(key, history, self.cache_ttl)
        except Exception:
            pass

    def _evaluate(self, history, now):
        """
        Progressive enforcement:
        First exceeded stage immediately applies its penalty.
        """

        for max_attempts, window, retry_after in self.stages:
            recent = [t for t in history if now - t < window]

            # if max_attempts is None:
            #     if recent:
            #         return False, retry_after
            #     continue
            if len(recent) >= max_attempts:
                return False, retry_after
        return True, 0
    def wait(self):
        return getattr(self, 'retry_after', None)
    def reset_on_success(self,request):
        cache=_get_cache()
        keys=self.build_cache_keys(request)
        for key in keys:
            try:
                cache.delete(key)
            except Exception :
                pass
    def allow_request(self, request, view):
        cache = _get_cache()
        now = time.time()

        keys = self.build_cache_keys(request)

        # Check all keys — most restrictive one wins
        most_restrictive_retry = 0
        blocked = False

        for key in keys:
            history = self._get_history(cache, key)
            allowed, retry_after = self._evaluate(history, now)
            if not allowed:
                blocked = True
                if retry_after > most_restrictive_retry:
                    most_restrictive_retry = retry_after
        retry_at=timezone.now()+timedelta(minutes=most_restrictive_retry)
        wait=most_restrictive_retry
        if blocked:
            from rest_framework.exceptions import Throttled
            raise  Throttled(
                wait=wait,
                detail="Too many actions."
            )
        # Allowed — record this attempt across all keys
        for key in keys:
            history = self._get_history(cache, key)
            history.append(now)
            # Trim history to cache_ttl to prevent unbounded growth
            history = [t for t in history if now - t < self.cache_ttl]
            self._set_history(cache, key, history)

        return True

    def wait(self):
        return getattr(self, 'retry_after', None)
  


    def throttle_failure_view(self, request, exc):
        """Can be called from views to record a confirmed failure separately."""
        pass


#  Login 

class LoginThrottle(ProgressiveThrottle):
    """
    Login accepts email OR username as identifier.
    Both are tracked alongside IP.

    Stage progression:
      5 attempts/min   → normal usage
      10 attempts/5min → slowing down, 30s penalty
      15 attempts/hr   → serious attempt, 5min penalty
      lockout          → 1hr block
    """
    scope = 'login'
    stages = [
        (5,    60,    0),
        (10,   300,   30),
        (15,   3600,  300),
        (25, 86400, 3600),
    ]

    def get_identifier_from_body(self, request):
        # LoginSerializer uses 'identifier' which can be email or username
        return request.data.get('identifier', None)


#  Register ─

class RegisterThrottle(ProgressiveThrottle):
    """
    Registration tracked by IP + email.
    Tighter than login — legitimate users register once.

    Stage progression:
      3 attempts/min   → normal (mistyped something, retrying)
      6 attempts/10min → suspicious, 1min penalty
      10 attempts/hr   → likely spam, 10min penalty
      lockout          → 2hr block
    """
    scope = 'register'
    stages = [
        (3,    60,    0),
        (5,    600,   60),
        (10,   3600,  600),
        (20, 86400, 7200),
    ]

    def get_identifier_from_body(self, request):
        return request.data.get('email', None)


#  Forgot Password 

class ForgotPasswordThrottle(ProgressiveThrottle):
    """
    Tracked by IP + email.
    Very tight — this triggers email sends and token generation.

    Stage progression:
      3 attempts/hr    → normal (user forgot they already requested)
      5 attempts/3hr   → suspicious, 15min penalty
      lockout          → 6hr block
    """
    scope = 'forgot_password'
    stages = [
        (3,    3600,   0),
        (5,    10800,  900),
        (10,   18000,  600),
        (None, 86400,  21600),
    ]

    def get_identifier_from_body(self, request):
        return request.data.get('email', None)


#  OTP Verify 

class OTPVerifyThrottle(ProgressiveThrottle):
    """
    Email verification OTP attempts.
    Tracked by IP + user_id (acts as identifier).
    Tight because OTP is only 6 digits — brute-forceable without this.

    Stage progression:
      5 attempts/5min  → normal
      8 attempts/30min → 2min penalty
      lockout          → 1hr block
    """
    scope = 'otp_verify'
    stages = [
        (5,    300,   0),
        (8,    1800,  120),
        (15, 86400, 3600)
    ]

    def get_identifier_from_body(self, request):
        # user_id is sent with OTP verify requests
        user_id = request.data.get('user_id', None)
        email=request.data.get('email', None)
        if user_id and email:
            return f'uid:{user_id}' 
        elif  user_id and not email:
            return f'uid:{user_id}'
        elif email and not user_id:
            return f'uid:{email}'
        else :
            return None


#  Resend OTP 

class ResendOTPThrottle(ProgressiveThrottle):
    """
    Resend OTP — triggers email send each time.
    Tracked by IP + user_id.

    Stage progression:
      3 attempts/10min → normal
      5 attempts/hr    → 5min penalty
      lockout          → 3hr block
    """
    scope = 'resend_otp'
    stages = [
        (3,    600,   0),
        (5,    3600,  300),
        (15, 86400, 10800),
    ]

    def get_identifier_from_body(self, request):
        user_id = request.data.get('user_id', None)
        email=request.data.get('email', None)
        if user_id and email:
            return f'uid:{user_id}' 
        elif  user_id and not email:
            return f'uid:{user_id}'
        elif email and not user_id:
            return f'uid:{email}'
        else:
            return None


#  Check Email ─

class CheckEmailThrottle(ProgressiveThrottle):
    """
    Email availability check — used during registration form.
    Tracked by IP + email being checked.
    Looser than auth endpoints but still prevents enumeration.

    Stage progression:
      20 attempts/min  → normal typing/checking
      50 attempts/5min → 30s penalty
      100 attempts/hr  → 5min penalty
      lockout          → 30min block
    """
    scope = 'check_email'
    stages = [
        (20,   60,    0),
        (50,   300,   30),
        (100,  3600,  300),
        (140, 86400, 1800),
    ]

    def get_identifier_from_body(self, request):
        return request.data.get('email', None)


#  Password Reset Confirm 

class ResetPasswordThrottle(ProgressiveThrottle):
    """
    Password reset confirmation — submitting new password with token.
    Tracked by IP only (no email in this request, just the token).

    Stage progression:
      5 attempts/10min → normal
      8 attempts/hr    → 5min penalty
      lockout          → 2hr block
    """
    scope = 'reset_password'
    stages = [
        (5,    600,   0),
        (8,    3600,  300),
        (20, 86400, 7200),
    ]
