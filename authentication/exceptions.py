from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled):
        wait = exc.wait  # seconds remaining

        if wait is None:
            message = "Too many requests. Please try again later."
            retry = None
        elif wait >= 3600:
            minutes = int(wait // 60)
            message = f"Too many attempts. Try again in {minutes} minutes."
            retry = int(wait)
        elif wait >= 60:
            minutes = int(wait // 60)
            seconds = int(wait % 60)
            message = f"Slow down. Try again in {minutes}m {seconds}s."
            retry = int(wait)
        else:
            message = f"Too many requests. Try again in {int(wait)} seconds."
            retry = int(wait)

        return Response({
            "error": message,
            "retry_after_seconds": retry,
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    return response
    