from django.db.models.signals import post_save, post_delete
from django.db.models import F
from django.db import transaction
from feed.feed_publisher import publish_new_feed_event,publish_update_feed_event,publish_feed_event
from .serializers import PostListSerializer
from django.conf import settings
from django.dispatch import receiver
from .models import (CommunityPost,CommunityPostUpvote, CommunityPostComment,CommunityCommentUpvote,
                     CommunityCommentDownvote,CommunitySavedPost,PostViews)
from authentication.models import Follow,CustomUser
from authentication.notification_service import notify

from django.contrib.auth import get_user_model
User=get_user_model()
@receiver(post_save,sender=CommunityPost)
def notify_seller_on_status_change(sender,instance,created,**kwargs):
    if created:
        return
    if instance.is_active==False:
        return
    if instance.status=="approved":
        notify(
        recipient=instance.owner,
        notification_type="post_approved",
        title="Your post was approved",
        body=f"{instance.name} was approved",
        data={
             "slug": instance.slug,
            # "username": instance.author.username,
            "community_name":instance.community.name,
            "community_slug":instance.community.slug},
        send_push=True,
    )
    if instance.status=="rejected":
        notify(
        recipient=instance.owner,
        notification_type="post_rejected",
        title="Your post was rejected",
        body=f"{instance.name} was rejected. Reason:{instance.rejection_reason}",
        data={
             "slug": instance.slug,
            # "username": instance.author.username,
            "community_name":instance.community.name,
            "community_slug":instance.community.slug},
        send_push=True,
    )
   
    #email sending and notifications required
@receiver(post_save, sender=PostViews)
def increment_views_count(sender, instance, created, **kwargs):
    if created:
        CommunityPost.objects.filter(id=instance.post_id).update(
            views_count=F("views_count") + 1
        )
        
@receiver(post_save, sender=CommunityPostUpvote)
def increment_post_upvotes(sender, instance, created, **kwargs):
    if created:
        CommunityPost.objects.filter(id=instance.post_id).update(
            upvotes_count=F("upvotes_count") + 1
        )
    def publish_after_commit():
        post=CommunityPost.objects.only("id","slug","upvotes_count").get(id=instance.post_id)
        publish_update_feed_event("change_upvotes_count_post-com", {
        "id": str(instance.post_id),
        "slug": post.slug,
        "upvotes_count": post.upvotes_count,
        "community_slug":post.community.slug,
    })
    transaction.on_commit(publish_after_commit)

@receiver(post_delete, sender=CommunityPostUpvote)
def decrement_post_upvotes(sender, instance, **kwargs):
    CommunityPost.objects.filter(id=instance.post_id).update(
        upvotes_count=F("upvotes_count") - 1
    )
    def publish_after_commit():
            post=CommunityPost.objects.only("id","slug","upvotes_count").get(id=instance.post_id)
            publish_update_feed_event("change_upvotes_count_post-com", {
        "id": str(instance.post_id),
        "slug": post.slug,
        "upvotes_count": post.upvotes_count,
        "community_slug":post.community.slug,
    })
    transaction.on_commit(publish_after_commit)


# comment count
@receiver(post_save, sender=CommunityPostComment)
def increment_comment_count(sender, instance, created, **kwargs):
    if instance.is_deleted:
        return
    if created:
        CommunityPost.objects.filter(id=instance.post_id).update(
            comments_count=F("comments_count") + 1
        )
        def publish_after_commit():
            post=CommunityPost.objects.only("id","slug","comments_count").get(id=instance.post_id)
            publish_update_feed_event("change_comments_count_post-com", {
            "id": str(instance.post_id),
            "slug": post.slug,
            "comments_count": post.comments_count,
            "community_slug":post.community.slug,
        })
        transaction.on_commit(publish_after_commit)
@receiver(post_delete, sender=CommunityPostComment)
def decrement_comment_count(sender, instance, **kwargs):
    CommunityPost.objects.filter(id=instance.post.id).update(
        comments_count=F("comments_count") - 1
    )
    def publish_after_commit():
        post=CommunityPost.objects.only("id","slug","comments_count").get(id=instance.post_id)
        publish_update_feed_event("change_comments_count_post-com", {
        "id": str(instance.post_id),
        "slug": post.slug,
        "comments_count": post.comments_count,
        "community_slug":post.community.slug,
    })
    transaction.on_commit(publish_after_commit)

# comment upvotes
@receiver(post_save, sender=CommunityCommentUpvote)
def increment_comment_upvotes(sender, instance, created, **kwargs):
    if created:
        CommunityPostComment.objects.filter(id=instance.comment.id).update(
            upvotes_count=F("upvotes_count") + 1
        )
        
@receiver(post_save, sender=CommunityCommentDownvote)
def increment_comment_downvotes(sender, instance, created, **kwargs):
    
    if created:
        CommunityPostComment.objects.filter(id=instance.comment_id).update(
            downvotes_count=F("downvotes_count") + 1
        )
@receiver(post_delete, sender=CommunityCommentUpvote)
def decrement_comment_upvotes(sender, instance, **kwargs):
    CommunityPostComment.objects.filter(id=instance.comment_id).update(
            upvotes_count=F("upvotes_count") - 1
        )
    
    
@receiver(post_delete, sender=CommunityCommentDownvote)
def decrement_comment_downvotes(sender, instance, **kwargs):
    CommunityPostComment.objects.filter(id=instance.comment_id).update(
            downvotes_count=F("downvotes_count") -1
        )




@receiver(post_save, sender=CommunitySavedPost)
def increment_saves_count(sender, instance, created, **kwargs):
    if created:
        CommunityPost.objects.filter(id=instance.post_id).update(
            saves_count=F("saves_count") + 1
        )
        def publish_after_commit():
            post=CommunityPost.objects.only("id","slug","comments_count").get(id=instance.post_id)
            publish_update_feed_event("change_saves_count_post-com", {
            "id": str(instance.post_id),
            "slug": post.slug,
            "saves_count": post.saves_count,
            "community_slug":post.community.slug,
        })
        transaction.on_commit(publish_after_commit)


@receiver(post_delete, sender=CommunitySavedPost)
def decrement_saves_count(sender, instance, **kwargs):
    
    CommunityPost.objects.filter(id=instance.post_id).update(
            saves_count=F("saves_count") - 1
        )
    def publish_after_commit():
        post=CommunityPost.objects.only("id","slug","comments_count").get(id=instance.post_id)
        publish_update_feed_event("change_saves_count_post-com", {
        "id": str(instance.post_id),
        "slug": post.slug,
        "saves_count": post.saves_count,
        "community_slug":post.community.slug,
    })
    transaction.on_commit(publish_after_commit)
    
@receiver(post_save, sender=CommunityPost)
def handle_post_count(sender, instance, created, **kwargs):
    
    if created:
        User.objects.filter(id=instance.owner.id).update(
            total_posts=F("total_posts") + 1
        )
    elif not instance.is_active:
        # soft deleted
        User.objects.filter(id=instance.owner.id).update(
            total_posts=F("total_posts") - 1
        )
        
        


@receiver(post_save, sender=CommunityPostUpvote)
def notify_post_upvote(sender, instance, created, **kwargs):
    if not created:
        return
    # don't notify if user likes their own post
    if instance.voter == instance.post.owner:
        return
    notify(
        recipient=instance.post.owner,
        notification_type="post_upvote",
        title="Someone liked your listing",
        body=f"@{instance.voter.username} liked {instance.post.name}",
        data={
            "slug": instance.post.slug,
            "username": instance.voter.username,
            "community_name":instance.post.community.name,
            "community_slug":instance.post.community.slug
        },
        send_push=True,
    )

@receiver(post_save, sender=CommunityPostComment)
def notify_new_comment(sender, instance, created, **kwargs):
    if not created:
        return
    # don't notify if owner comments on own post
    if instance.author == instance.post.owner:
        return
    notify(
        recipient=instance.post.owner,
        notification_type="new_comment",
        title="New comment on your listing",
        body=f"@{instance.author.username}: {instance.body[:60]}",
        data={
            "slug": instance.post.slug,
            "username": instance.author.username,
            "community_name":instance.post.community.name,
            "community_slug":instance.post.community.slug
        },
        send_push=True,
    )


    
    
    
    
    
    
    
@receiver(post_save, sender=CommunityPostComment)
def update_reply_count(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.parent:
        # increment parent's reply count
        CommunityPostComment.objects.filter(id=instance.parent.id).update(
            replies_count=F("replies_count") + 1
        )
    else:
        # top-level comment — increment post comment count
        CommunityPost.objects.filter(id=instance.post.id).update(
            comments_count=F("comments_count") + 1
        )




       





def fix_media_urls(data: dict) -> dict:
    base = settings.DJANGO_BASE_URL.rstrip("/")
    
    def make_absolute(path):
        if not path or str(path).startswith("http"):
            return path
        return f"{base}/{str(path).lstrip('/')}"
    
    # fix images array
    if "images" in data:
        data["images"] = [
            {**img, "image": make_absolute(img.get("image"))}
            for img in data["images"]
        ]
    
    # fix videos array if you have one
    if "videos" in data:
        data["videos"] = [
            {**vid, "video": make_absolute(vid.get("video"))}
            for vid in data["videos"]
        ]

    # fix single thumbnail/cover if exists
    for field in ("thumbnail", "cover", "image"):
        if field in data:
            data[field] = make_absolute(data[field])

    return data
# ── FIRE when post gets approved ──────────────────────────
@receiver(post_save, sender=CommunityPost)
def publish_post_approved(sender, instance, created, **kwargs):
    # only fire when status flips TO approved
    if instance.status != "approved" or not instance.is_active:
        return
    data = PostListSerializer(instance).data
    publish_new_feed_event("new_post-com", fix_media_urls(data))


# ── FIRE when post is soft-deleted ────────────────────────
@receiver(post_save, sender=CommunityPost)
def publish_post_removed(sender, instance, created, **kwargs):
    if instance.is_active:
        return  # not deleted
    publish_feed_event("post_removed-com", {
        "id": str(instance.id),
        "slug": instance.slug,
        "community_slug":instance.community.slug
    })


#── FIRE when price or details update on a live post ──────
# @receiver(post_save, sender=Post)
# def publish_post_updated(sender, instance, created, **kwargs):
#     if created:
#         return  # new post, not an update
#     if instance.status != "approved" or not instance.is_active:
#         return
#     publish_update_feed_event("post_updated", {
#         "id": str(instance.id),
#         "slug": instance.slug,
#         "price": str(instance.price),
#         "name": instance.name,
#     })
    
    
    
    
    
    
    
    
