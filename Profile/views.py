

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from authentication.models import Follow
from .models import ProfilePrivacy
from .serializers import ProfilePrivacySerializer


class ProfilePrivacyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's privacy settings"""
        privacy = request.user.privacy
        serializer = ProfilePrivacySerializer(privacy)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=200)

    def patch(self, request):
        """Update privacy settings - partial update"""
        privacy = request.user.privacy
        serializer = ProfilePrivacySerializer(
            privacy, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Privacy settings updated",
                "data": serializer.data
            }, status=200)
        return Response(serializer.errors, status=400)
        
