from django.contrib import admin
from .models import (Community,Membership,CommunityInvites,CommunityCategoryPost,
                     CommunityPost,CommunitySavedPost,CommunityPostReport,
                     CommunityPostImage,CommunityPostVideo,
                     CommunityPostComment,CommunityJoinRequest,CommunityCommentUpvote,CommunityCommentDownvote,CommunityPostUpvote)
@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display=["name","creator","members_count"]
    list_filter=["privacy","creator"]
    search_fileds=['creator',"name"]
    
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display=["user","community","role","status"]
    list_filter=["community","status"]
    search_fileds=['community',"status"]
    
@admin.register(CommunityInvites)
class CommunityInvitesAdmin(admin.ModelAdmin):
    list_display=["community__name","inviter","invited"]
    list_filter=["community","status"]
    search_fileds=['inviter',"invited","community"]


@admin.register(CommunityCategoryPost)
class CommunityCategoryPostAdmin(admin.ModelAdmin):
    list_display=["name","slug","is_active","order"]
    prepopulated_fields={"slug":("name",)}
    list_editable=["is_active"]

@admin.register(CommunityPost)
class PostAdmin(admin.ModelAdmin):
    list_display=["name","owner","status","is_active","category","community"]
    list_filter=["status","category","community"]
    list_editable=["is_active","status"]
    search_fields=["name","owner__username"]
    actions=["approve_posts","reject_posts"]
    @admin.action(description="Approve selected posts")
    def approve_posts(self,request,queryset):
        queryset.update(status="approved")
    @admin.action(description="Reject selected posts")
    def reject_posts(self,request,queryset):
        queryset.update(status="rejected")

@admin.register(CommunityPostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display=["post","order","owner","is_cover"]
    list_editable=["order","is_cover"]


    
@admin.register(CommunityPostComment)
class CommentAdmin(admin.ModelAdmin):
    list_display=["post","author","body","created_at","is_active","is_edited"
                  ]
    search_fields=["post__name","author__username","body"]

@admin.register(CommunityCommentUpvote)
class CommentUpvoteAdmin(admin.ModelAdmin):
    list_display=["comment","owner","created_at"]
    search_fields=["comment__text","owner__username"]

@admin.register(CommunityCommentDownvote)
class CommentDownvoteAdmin(admin.ModelAdmin):
    list_display=["comment","owner","created_at"]
    search_fields=["comment__text","owner__username"]



@admin.register(CommunitySavedPost)
class SavedPost(admin.ModelAdmin):
    list_display=["post","user","created_at"]
    search_fields=["post__name","user__username"]

@admin.register(CommunityPostVideo)
class PostVideo(admin.ModelAdmin):
    list_display=["post","owner","created_at"]
    search_fields=["post__name","owner__username"]
    


    




@admin.register(CommunityPostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display=["post","reporter","created_at"]
    search_fields=["id","post__name","reporter_name"]
    
@admin.register(CommunityPostUpvote)
class PostReportAdmin(admin.ModelAdmin):
    list_display=["post"]
    search_fields=["post__name"]
    
@admin.register(CommunityJoinRequest)
class CommunityJoinRequestAdmin(admin.ModelAdmin):
    list_display=["requester","status","community"]
    search_fields=["requester","community"]














