# communities/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid
User = get_user_model()
from feed.models import generate_post_slug
from cloudinary_storage.storage import VideoMediaCloudinaryStorage

class Community(models.Model):
    """The group itself"""
    PRIVACY_CHOICES = [
        ('public', 'Public'),       # Anyone can see & join
        ('private', 'Private'),     # Must request to join
        ('invite', 'Invite Only'),  # Admin sends invite
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='communities/', blank=True)
    category = models.CharField(max_length=50,null=True,blank=True)   
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_communities')
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)
    members_count=models.PositiveIntegerField(default=0,null=True,blank=True)
    rules=models.JSONField(default=list)
    class Meta:
        verbose_name_plural = 'communities'

    def __str__(self):
        return f"{self.name} : {self.creator}"
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=generate_post_slug(self.name)
        super().save(*args,**kwargs)

class Membership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('banned', 'Banned'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    asigned_roles=models.JSONField(default=list)
    class Meta:
        unique_together = ('user', 'community')  # One membership per user per community
    def __str__(self):
        return f"{self.community.name}:{self.role}"
    def is_admin(self):
        return self.role == 'admin'

    def can_moderate(self):
        return self.role in ('admin', 'moderator')
class CommunityInvites(models.Model):
    
    STATUS=[
        ("accepted","Accepted"),
        ("pending","Pending"),
        
    ]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='invites')

    inviter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="goup_inviter")
    invited=models.ForeignKey(User,on_delete=models.CASCADE,related_name="group_invites")
    created_at=models.DateTimeField(auto_now_add=True)
    status=models.CharField(max_length=10, choices=STATUS,default="pending")
    class  Meta:
        verbose_name = 'Community membership invite'
        unique_together=("inviter","invited","community")
        verbose_name_plural = 'Community membership invites'
    def __str__(self):
        return f"{self.inviter.username}⇒{self.invited.username}-{self.community.name}"
class CommunityJoinRequest(models.Model):
    
    STATUS=[
        ("accepted","Accepted"),
        ("pending","Pending"),
        ("rejected","Rejected")
        
    ]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='join_requests')

    requester=models.ForeignKey(User,on_delete=models.CASCADE,related_name="goup_join_requests")
    created_at=models.DateTimeField(auto_now_add=True)
    status=models.CharField(max_length=10, choices=STATUS,default="pending")
    class  Meta:
        verbose_name = 'Community membership Join Requests'
        unique_together=("requester","community")
        
    def __str__(self):
        return f"{self.requester.username}⇒{self.community.name}"
    
class CommunityCategoryPost(models.Model):
    
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100,unique=True)
    community=models.ForeignKey(Community,on_delete=models.CASCADE,related_name="community_categories")
    slug=models.SlugField(unique=True,blank=True)
    icon=models.CharField(max_length=50,blank=True,null=True)
    description=models.TextField(blank=True,null=True)
    is_active=models.BooleanField(default=True)
    order=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = 'CommunityCategoryPost'
        verbose_name_plural = 'Community Category Posts'
    def __str__(self):
        return self.name
    def save(self,*args,**kwargs):
        if not self.slug and self.name:
            self.slug=generate_post_slug(self.name)
        super().save(*args,**kwargs)
        
        
class CommunityPost(models.Model):
    category=models.ForeignKey(CommunityCategoryPost,on_delete=models.SET_NULL,related_name="posts",null=True)
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_posts")
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    community=models.ForeignKey(Community,on_delete=models.CASCADE,related_name="community_posts")
    name=models.CharField(max_length=100,blank=True,null=True)
    slug=models.SlugField(max_length=200,unique=True,blank=True)
    TYPES=(
        ("text","Text"),
        ("image","Image"),
        ("video","Video"),
    )
    post_type=models.CharField(max_length=10,choices=TYPES,default="text")
    description=models.TextField()
    location_display=models.CharField()
    location_lat=models.FloatField(null=True,blank=True)
    location_lng=models.FloatField(null=True,blank=True)
    STATUS=(
        ("approved","Aproved"),
        ("pending","Pending"),
        ("rejected","Rejected"),
    )
    status=models.TextField(choices=STATUS,default="pending")
    rejection_reason=models.TextField(blank=True,null=True)
    sponsored=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    client_upload_id = models.UUIDField(unique=True, null=True, blank=True, db_index=True)
    is_active=models.BooleanField(default=True)
    
    
    
    upvotes_count=models.PositiveIntegerField(default=0)
    comments_count=models.PositiveIntegerField(default=0)
    views_count=models.PositiveIntegerField(default=0)
    saves_count=models.PositiveIntegerField(default=0)
    
    
    class Meta:
        verbose_name = 'Community Post'
        verbose_name_plural = 'Community Posts'
        constraints = [
                models.CheckConstraint(
            condition=models.Q(post_type__in=["text", "image", "video"]),
            name="valid_post_type_com"
        ),
                models.CheckConstraint(
            condition=models.Q(status__in=["approved", "pending", "rejected"]),
            name="valid_status_com"
        ),
    ]
    def __str__(self):
        return f"{self.owner.username}'s post:{self.name}"
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=generate_post_slug(self.name)
        super().save(*args,**kwargs)



class CommunitySavedPost(models.Model):
    id=models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_saved_posts")
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="community_saved_by")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("user","post")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.user.username} saved {self.post.name}"

class CommunityPostReport(models.Model):
    REASON_CHOICES = (
        ("Spam or scam", "Spam or scam"),
        ("Fake Account", "Fake Account"),
        ("Harassment", "Harassment"),
        ("Inappropriate Content", "Inappropriate Content"),
        ("Inappropriate Behavior","Inappropriate Behavior"),
        ("Impersonation", "Impersonation"),
        ("Other", "Other"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("dismissed", "Dismissed"),
    )

    ACTION_CHOICES = (
        ("none", "No Action"),
        ("warn", "Warning Issued"),
        ("suspend", "Account Suspended"),
        ("ban", "Account Banned"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="community_podutreports_filed"
    )
    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name="community_post_reports_received"
    )
    reason = models.CharField(max_length=1000, choices=REASON_CHOICES)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, default="none")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="community_post_reports_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'CommunityPostReport'
        unique_together = ("reporter", "post", "reason")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reporter} report on {self.post}"


class CommunityPostImage(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="images")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_images")
    image=models.ImageField(upload_to="posts/images/")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = 'CommunityPostImage'
    def __str__(self):
        return f"{self.post.name}'s image"
    
class CommunityPostVideo(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="videos")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_videos")
    video=models.FileField(storage=VideoMediaCloudinaryStorage(),blank=True, null=True,upload_to="posts/videos/")
    processing_status = models.CharField(
        max_length=10,
        choices=[("processing", "Processing"), ("done", "Done"), ("failed", "Failed")],
        default="processing",
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = 'CommunityPostVideo'
    def __str__(self):
        return f"{self.post.name}'s video"
class CommunityPostUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="community_upvotes")
    voter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_upvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = 'CommunityPostUpvotes'
        unique_together=("post","voter")
    def __str__(self):
        return f"{self.voter.username} vote for {self.post.id}"

    

    
class CommunityPostComment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="community_comments")
    author=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_comments")
    parent=models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies")
    replied_to=models.ForeignKey( #the actual comment being replied to
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_replies")
    reply_to=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_reply_to",null=True,blank=True)
    body=models.CharField()
    deleted_body=models.CharField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)
    downvotes_count=models.PositiveIntegerField(default=0)
    upvotes_count=models.PositiveIntegerField(default=0)
    replies_count=models.PositiveIntegerField(default=0)
    reporter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_reporter_comments",null=True,blank=True)
    is_reported=models.BooleanField(default=False)
    report_reason=models.CharField(blank=True,null=True)
    is_edited=models.BooleanField(default=False)
    
    class  Meta:
        verbose_name_plural = 'CommunityPostComment'
        ordering=["-created_at"]
    def __str__ (self):
        return f"{self.author.username}'s comment on {self.post.name} : {self.body}"
        
class CommunityCommentUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(CommunityPostComment,on_delete=models.CASCADE,related_name="community_comment_upvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_owner_upvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = 'CommunityCommentUpvotes'
        unique_together=("comment","owner")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
class CommunityCommentDownvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(CommunityPostComment,on_delete=models.CASCADE,related_name="comment_downvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="community_owner_downvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("comment","owner")
        verbose_name_plural = 'CommunityCommentDownvotes'
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
    

class PostViews(models.Model):
    post=models.ForeignKey(CommunityPost,on_delete=models.CASCADE,related_name="post_views_groups")
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="user_post_views_groups")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("post","user")
    def __str__(self):
        return f"{user}:{post}"
    
        

        
    
















