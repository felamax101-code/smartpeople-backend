from django.contrib import admin
from .models import (Post,Category,PostImage,Review,SavedPost,
                    Comment, CommentUpvote,CommentDownvote,PostVideo,
                    PostReport,PropertyProfile,ListingApplication,PostViews)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display=["name","slug","is_active","order"]
    prepopulated_fields={"slug":("name",)}
    list_editable=["is_active"]
@admin.register(PropertyProfile)
class PropertyProfileAdmin(admin.ModelAdmin):
    list_display=["user","name","org_name","can_post_listings"]
    
@admin.register(ListingApplication)
class PropertyProfileAdmin(admin.ModelAdmin):
    list_display=["user","name","applicant_type","status"]
 


  
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display=["name","owner","status","is_active","category","created_at","updated_at"]
    list_filter=["status","category"]
    list_editable=["is_active","status"]
    search_fields=["name","owner__username"]
    
    actions=["approve_posts","reject_posts"]
    @admin.action(description="Approve selected posts")
    def approve_posts(self,request,queryset):
        queryset.update(status="approved")
    @admin.action(description="Reject selected posts")
    def reject_posts(self,request,queryset):
        queryset.update(status="rejected")

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display=["post","order","owner","is_cover"]
    list_editable=["order","is_cover"]


    
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display=["post","author","body","created_at","is_active","is_edited"
                  ]
    search_fields=["post__name","author__username","body"]

@admin.register(CommentUpvote)
class CommentUpvoteAdmin(admin.ModelAdmin):
    list_display=["comment","owner","created_at"]
    search_fields=["comment__text","owner__username"]

@admin.register(CommentDownvote)
class CommentDownvoteAdmin(admin.ModelAdmin):
    list_display=["comment","owner","created_at"]
    search_fields=["comment__text","owner__username"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display=["reviewer","target","comment","created_at"]
    search_fields=["reviewer__username","target__username","comment"]
@admin.register(SavedPost)
class SavedPost(admin.ModelAdmin):
    list_display=["post","user","created_at"]
    search_fields=["post__name","user__username"]

@admin.register(PostVideo)
class PostVideo(admin.ModelAdmin):
    list_display=["post","owner","created_at"]
    search_fields=["post__name","owner__username"]
    





@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display=["post","reporter","created_at"]
    search_fields=["id","post__name","reporter_name"]

@admin.register(PostViews)
class PostViewsAdmin(admin.ModelAdmin):
    list_display=["post","user"]
    search_fields=["post"]













