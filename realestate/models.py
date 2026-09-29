from django.db import models
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from cloudinary_storage.storage import VideoMediaCloudinaryStorage

#helper functions
def generate_post_slug(name):
    base_slug=slugify(name.lower())
    suffix=str(uuid.uuid4())[:8]
    return f"{base_slug}-{suffix}"

class PropertyProfile(models.Model):
    """
    Self-contained house-hunting identity for a user.
    Keeps propertyhunting fully decoupled from the core User/other apps —
    created lazily (get_or_create) the first time it's needed, not on user signup.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_profile",
    )
    name=models.CharField(max_length=50,blank=True,null=True)
    org_name=models.CharField(max_length=50,blank=True,null=True)
    can_post_listings = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PropertyProfile({self.user}) - can_post={self.can_post_listings}"


class ListingApplication(models.Model):
    APPLICANT_TYPE_CHOICES = [
        ("personal", "Personal"),
        ("organization", "Organization"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_applications",
    )
    applicant_type = models.CharField(max_length=12, choices=APPLICANT_TYPE_CHOICES)
    name = models.CharField(max_length=255,blank=True,null=True)  # full name if personal, org name if organization

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_listing_applications",
    )
    rejection_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.applicant_type}) - {self.status}"
class Category(models.Model):
    
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100,unique=True)
    slug=models.SlugField(unique=True,blank=True)
    icon=models.CharField(max_length=50,blank=True,null=True)
    description=models.TextField(blank=True,null=True)
    is_active=models.BooleanField(default=True)
    order=models.PositiveIntegerField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=slugify(self.name)
        super().save(*args,**kwargs)
    
    


class Post(models.Model):
    LISTING_TYPES=(
        ("rental","Rental"),
        ("sale","Sale")
    )
    category=models.ForeignKey(Category,on_delete=models.SET_NULL,related_name="spposts",null=True,blank=True)
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spposts")
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
    listing_type=models.CharField(choices=LISTING_TYPES,default="rental")
    deposit=models.PositiveIntegerField(default=0)
    monthly_installment=models.PositiveIntegerField(default=0)
    STATUS=(
        ("approved","Aproved"),
        ("pending","Pending"),
        ("rejected","Rejected"),
    )
    HOUSE_TYPE=(
        ("single","Single Room"),
        ("bed_sitter","BedSitter"),
        ("one_bedroom","One Bedroom"),
        ("two_bedroom","Two Bedroom"),
        ("three_plus","Three+ Bedroom"),
    )
    status=models.TextField(choices=STATUS,default="pending")
    rejection_reason=models.TextField(blank=True,null=True)
    sponsored=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    price=models.IntegerField(default=0)
    is_active=models.BooleanField(default=True)
    house_type=models.CharField(choices=HOUSE_TYPE,default="single")
    
    
    upvotes_count=models.PositiveIntegerField(default=0)
    comments_count=models.PositiveIntegerField(default=0)
    views_count=models.PositiveIntegerField(default=0)
    saves_count=models.PositiveIntegerField(default=0)
    client_upload_id = models.UUIDField(unique=True, null=True, blank=True, db_index=True)
    
    class Meta:
       
        
        constraints = [
                models.CheckConstraint(
            condition=models.Q(post_type__in=["text", "image", "video"]),
            name="sp_valid_post_type"
        ),
                models.CheckConstraint(
            condition=models.Q(status__in=["approved", "pending", "rejected"]),
            name="sp_valid_status"
        ),
    ]
    def __str__(self):
        return f"{self.owner.username}'s post:{self.name}"
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=generate_post_slug(self.name)
        super().save(*args,**kwargs)



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
        related_name="spreports_filed"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="sppost_reports_received"
    )
    reason = models.CharField(max_length=1000, choices=REASON_CHOICES)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, default="none")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sppost_reports_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reporter", "post", "reason")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
            condition=models.Q(action_taken__in=["none", "warn", "suspend","ban"]),
            name="sp_valid_action_type"
        ),
    ]

    def __str__(self):
        return f"{self.reporter} report on {self.post}"


class PostImage(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="spimages")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spimages")
    image=models.ImageField(upload_to="posts/images/")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    def __str__(self):
        return f"{self.post.name}'s image"
    
class PostVideo(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="spvideos")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spvideos")
    video=models.FileField(storage=VideoMediaCloudinaryStorage(),blank=True, null=True,upload_to="posts/videos/")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    order=models.PositiveIntegerField(default=0)
    is_cover=models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=10,
        choices=[("processing", "Processing"), ("done", "Done"), ("failed", "Failed")],
        default="processing",
    )
    def __str__(self):
        return f"{self.post.name}'s video"
class PostUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="spupvotes")
    voter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spupvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("post","voter")
    def __str__(self):
        return f"{self.voter.username} vote for {self.post.id}"

    
class Review(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    
    comment=models.CharField()
    user_reply=models.CharField(null=True,blank=True)
    rating=models.PositiveSmallIntegerField(default=0)
    help_full=models.PositiveIntegerField(default=0)
    reviewer=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spreviewer")
    target=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spreview_target")
    created_at=models.DateTimeField(auto_now_add=True)
    
    class  Meta:
        unique_together=("reviewer","target")
    def __str__ (self):
        return f"{self.reviewer.username}'s review on {self.target.username}"
    
class Comment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="spcomments")
    author=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spcomments")
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
        related_name="spdirect_replies")
    reply_to=models.ForeignKey(User,on_delete=models.CASCADE,related_name="sp_reply_to",null=True,blank=True) #the user being replied to
    body=models.CharField()
    deleted_body=models.CharField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)
    downvotes_count=models.PositiveIntegerField(default=0)
    upvotes_count=models.PositiveIntegerField(default=0)
    replies_count=models.PositiveIntegerField(default=0)
    reporter=models.ForeignKey(User,on_delete=models.CASCADE,related_name="sp_reporter_comments",null=True,blank=True)
    is_reported=models.BooleanField(default=False)
    report_reason=models.CharField(blank=True,null=True)
    is_edited=models.BooleanField(default=False)
    
    class  Meta:
        ordering=["-created_at"]
    def __str__ (self):
        return f"{self.author.username}'s comment on {self.post.name} : {self.body}"
        
class CommentUpvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(Comment,on_delete=models.CASCADE,related_name="comment_upvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="sp_owner_upvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("comment","owner")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
class CommentDownvote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    comment=models.ForeignKey(Comment,on_delete=models.CASCADE,related_name="comment_downvotes")
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name="sp_owner_downvotes")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("comment","owner")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.owner.username} liked {self.comment.id}"
    


    
        
class SavedPost(models.Model):
    id=models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="spsaved_posts")
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="saved_by")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("user","post")
        ordering=["-created_at"]
    def __str__(self):
        return f"{self.user.username} saved {self.post.name}"
        
   
class PostViews(models.Model):
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name="sp_post_views")
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="sp_user_post_views")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=("post","user")
    def __str__(self):
        return f"{self.user}:{self.post}"
