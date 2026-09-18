from django.db import models
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import FileExtensionValidator

#helper functions
def generate_post_slug(name):
    base_slug=slugify(name.lower())
    suffix=str(uuid.uuid4())[:8]
    return f"{base_slug}-{suffix}"
class Category(models.Model):
    
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100,unique=True)
    slug=models.SlugField(unique=True,blank=True)
    icon=models.CharField(max_length=50,blank=True,null=True)
    description=models.TextField(blank=True,null=True)
    is_active=models.BooleanField(default=True)
    order=models.PositiveIntegerField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'Categories'
    def __str__(self):
        return self.name
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=slugify(self.name)
        super().save(*args,**kwargs)
    
    


class Post(models.Model):
    category=models.ForeignKey(Category,on_delete=models.SET_NULL,related_name="posts",null=True,blank=True)
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="posts")
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
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
    
    is_active=models.BooleanField(default=True)
    
    
    
    upvotes_count=models.PositiveIntegerField(default=0)
    comments_count=models.PositiveIntegerField(default=0)
    views_count=models.PositiveIntegerField(default=0)
    saves_count=models.PositiveIntegerField(default=0)
    
    
    class Meta:
        db_table = 'Posts'
        
        constraints = [
                models.CheckConstraint(
            condition=models.Q(post_type__in=["text", "image", "video"]),
            name="valid_post_type"
        ),
                models.CheckConstraint(
            condition=models.Q(status__in=["approved", "pending", "rejected"]),
            name="valid_status"
        ),
    ]
    def __str__(self):
        return f"{self.owner.username}'s post:{self.name}"
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=generate_post_slug(self.name)
        super().save(*args,**kwargs)

class PostRepost(models.Model):
    reposter=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reposts"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="reposts"
    )
    reposted_from=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reposted_from"
    )
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)

class PostReport(models.Model):
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
        related_name="podutreports_filed"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="post_reports_received"
    )
    reason = models.CharField(max_length=1000, choices=REASON_CHOICES)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, default="none")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="post_reports_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Post Reports"
        unique_together = ("reporter", "post", "reason")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
            condition=models.Q(action_taken__in=["none", "warn", "suspend","ban"]),
            name="valid_action_type"
        ),
    ]

    def __str__(self):
        return f"{self.reporter} report on {self.post}"


class PostImage(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="images")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="images")
    image=models.ImageField(upload_to="posts/images/")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    class Meta:
        db_table = 'Post images'
    def __str__(self):
        return f"{self.post.name}'s image"
    
class PostVideo(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="videos")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="videos")
    video=models.FileField(upload_to="posts/videos/")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    class Meta:
        db_table = 'Post videos'
    def __str__(self):
        return f"{self.post.name}'s video"
class PostUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="upvotes")
    voter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="upvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="Post upvotes"
        unique_together=("post","voter")
    def __str__(self):
        return f"{self.voter.username} vote for {self.post.id}"

    
class Review(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    
    comment=models.CharField()
    user_reply=models.CharField(null=True,blank=True)
    rating=models.PositiveSmallIntegerField(default=0)
    help_full=models.PositiveIntegerField(default=0)
    reviewer=models.ForeignKey(User,on_delete=models.CASCADE,related_name="reviewer")
    target=models.ForeignKey(User,on_delete=models.CASCADE,related_name="review_target")
    created_at=models.DateTimeField(auto_now_add=True)
    
    class  Meta:
        db_table = 'Review'
        unique_together=("reviewer","target")
    def __str__ (self):
        return f"{self.reviewer.username}'s review on {self.target.username}"
    
class Comment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="comments")
    author=models.ForeignKey(User,on_delete=models.CASCADE,related_name="comments")
    parent=models.ForeignKey(#top level comment 
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
    reply_to=models.ForeignKey(User,on_delete=models.CASCADE,related_name="reply_to",null=True,blank=True) #the user being replied to
    body=models.CharField()
    deleted_body=models.CharField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)
    downvotes_count=models.PositiveIntegerField(default=0)
    upvotes_count=models.PositiveIntegerField(default=0)
    replies_count=models.PositiveIntegerField(default=0)
    reporter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="reporter_comments",null=True,blank=True)
    is_reported=models.BooleanField(default=False)
    report_reason=models.CharField(blank=True,null=True)
    is_edited=models.BooleanField(default=False)
    
    class  Meta:
        db_table = 'Comment'
        ordering=["-created_at"]
    def __str__ (self):
        return f"{self.author.username}'s comment on {self.post.name} : {self.body}"
        
class CommentUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(Comment,on_delete=models.CASCADE,related_name="comment_upvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="owner_upvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="Comment upvotes"
        unique_together=("comment","owner")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
class CommentDownvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(Comment,on_delete=models.CASCADE,related_name="comment_downvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="owner_downvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="Comment downvotes"
        unique_together=("comment","owner")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
    


    
        
class SavedPost(models.Model):
    id=models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="saved_posts")
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="saved_by")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="Saved Posts"
        unique_together=("user","post")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.user.username} saved {self.post.name}"
        
    


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        User,
        through="ConversationParticipant",
        related_name="conversations",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="conversations"
    )
    last_message_preview = models.CharField(max_length=100, null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=100, null=True, blank=True)
    group_avatar = models.ImageField(upload_to="groups/avatars/",max_length=500, null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_conversations",
        db_column="created_by_id",
    )
    class Meta:
        db_table = "conversations"

    def __str__(self):
        return f"Conversation {self.id}"


class Message(models.Model):
    MESSAGE_TYPES = (
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("offer", "Offer"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default="text")
    body = models.TextField(null=True, blank=True)
    image_url = models.ImageField(upload_to="messages/images/",null=True, blank=True)
    video_url = models.FileField(upload_to="messages/videos/",null=True, blank=True,validators=[FileExtensionValidator(allowed_extensions=["mp4", "mov", "avi", "webm"])],)
    offer_data = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_reported= models.BooleanField(default=False,null=True,blank=True)
    report_reason= models.CharField(null=True, blank=True)
    reply_to = models.ForeignKey(
        "self",                        # self-referencing — points to another Message
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",        # message.replies.all() gives all replies to it
        db_column="reply_to_id",      
    )
    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        constraints = [
        models.CheckConstraint(
            condition=models.Q(message_type__in=["text", "image", "video","offer"]),
            name="valid_message_type"
        ),
    ]

    def __str__(self):
        return f"Message {self.id} in {self.conversation.id}"
    
    
    
    

class ConversationParticipant(models.Model):
    """
    Explicit through model so Django knows about is_admin and joined_at.
    Django will never call .add()/.set() on this — FastAPI owns all writes.
    This model exists purely so makemigrations generates the right schema.
    """

    conversation = models.ForeignKey(
        "Conversation",
        on_delete=models.CASCADE,
        db_column="conversation_id",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="customuser_id",  
    )
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "conversations_participants" 
        unique_together = ("conversation", "user")
        
        
        
class MessageRead(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    message=models.ForeignKey(
        Message,on_delete=models.CASCADE,db_column="message_id")
    user= models.ForeignKey( User,on_delete=models.CASCADE,db_column="user_id")
    read_at= models.DateTimeField(
                    default=timezone.now
                )
    class Meta:
        db_table="message_reads"
        constraints=[models.UniqueConstraint(
                fields=["user", "message"],
                name="uq_message_reads_msg_user",
            )]
        


    
    
    
class MessageReaction(models.Model):
    """
    One row = one user reacted with one emoji to one message.
    The unique constraint means a user can't add the same emoji twice
    to the same message but CAN add different emojis.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
        db_column="message_id",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="message_reactions",
        db_column="user_id",
    )
    # stores the emoji character directly"
    # max_length=10 covers multi-codepoint emojis like flags
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_reactions"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"],
                name="uq_reaction_per_emoji",
            )
        ]
        
class MessageDeletes(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    message=models.ForeignKey(
        Message,on_delete=models.CASCADE,db_column="message_id",related_name="message_deletes")
    user= models.ForeignKey( User,on_delete=models.CASCADE,db_column="user_id",related_name="message_deletes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'message_deletes'
        unique_together=("user","message")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "message"],
                name="uq_message_delete_per_user",
            )
        ]
    def __str__(self):
        return f"{self.user} :{self.message}"
        
class ConversationDeletes(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    conversation=models.ForeignKey(
        Conversation,on_delete=models.CASCADE,db_column="conversation_id",related_name="conversation_deletes")
    user= models.ForeignKey( User,on_delete=models.CASCADE,db_column="user_id",related_name="conversation_deletes")
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    class Meta:
        db_table = 'conversation_deletes'
        constraints = [
            models.UniqueConstraint(
                fields=["user", "conversation"],
                name="uq_conversation_delete_per_user",
            )
        ]
    
    
    def __str__(self):
        return f"{self.user} :{self.conversation}"
        
class PostViews(models.Model):
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="post_views")
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="user_post_views")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("post","user")
    def __str__(self):
        return f"{user}:{post}"