# communities/permissions.py
from rest_framework.permissions import BasePermission
from .models import Membership
from django.db.models import Q


class IsCommunityMember(BasePermission):
    """User must be an active member"""
    def has_object_permission(self, request, view, obj):
        # obj is the Community instance
        return Membership.objects.filter(
            user=request.user,
            community=obj,
            status='active'
        ).exists()


class IsCommunityModerator(BasePermission):
    """User must be admin or moderator"""
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            user=request.user,
            community=obj,
            role__in=['admin', 'moderator'],
            status='active'
        ).exists()


class IsCommunityAdmin(BasePermission):
    """Only admin can do this (e.g. delete community, change settings)"""
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            user=request.user,
            community=obj,
            role='admin',
            status='active'
        ).exists()
        
class IsAdminOrStaff(BasePermission):
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role in ("admin","staff")
    
class IsCommunityAdminOrIsCommunityModerator(BasePermission):
    def has_object_permission(self,request,view,obj):
        return Membership.objects.filter(
           Q (user=request.user) &
          Q  (community=obj) &
           (Q(role="admin")  or Q(role="moderator")) &
           Q (status='active')
        ).exists()