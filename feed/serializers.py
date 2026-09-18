from rest_framework import serializers
from .sanitize import sanitize_plain,sanitize_post_content
from .upload import upload_image,upload_video
from .models import ( Post,PostImage,Category,Comment,SavedPost,PostVideo,Review,
                     CommentUpvote,PostUpvote,CommentDownvote,PostReport)
from django.contrib.auth import get_user_model
User=get_user_model()
from django.utils import timezone

class SearchUsersSerializer(serializers.ModelSerializer):
    avatar=serializers.SerializerMethodField()
    class Meta:
        model=User
        fields=["id","username","followers","avatar"]
        
    def get_avatar(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if obj.avatar:
            return request.build_absolute_uri(obj.avatar.url) 
        return None
        
class UserSerializer(serializers.ModelSerializer):
    """Full user info — for /users/me/"""
    
    verification_badge=serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'id', 'username', 'name',  'avatar',
            "verification_badge",
            
             
        ]
        
    def get_verification_badge(self,obj):
        badge=obj.verification_badge
        return {
                "label":badge.get("label"),
                "color":badge.get("color"),
                "icon":badge.get("icon")
        }
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model=Category
        fields=["id","name","slug","icon","description","order"]
        
        
class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model=PostImage
        fields=["id","image","order"]


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model=PostVideo
        fields=["id","video","order"]
class PostListSerializer(serializers.ModelSerializer):
    is_upvoted=serializers.SerializerMethodField()
    owner=UserSerializer(read_only=True)
    is_saved=serializers.SerializerMethodField()
    images=ImageSerializer(many=True,read_only=True)
    videos=VideoSerializer(many=True,read_only=True)
    category=CategorySerializer(read_only=True)
    class Meta:
        model=Post
        fields=["id","name","description","post_type","saves_count",
                "category","images","slug",
                "views_count","upvotes","comments_count","is_upvoted","sponsored",
                "status","owner","location_display","location_lat","location_lng",
                "status","is_saved","upvotes_count",
                "created_at","videos"]

        
            
        
    def get_is_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return PostUpvote.objects.filter(post=obj,voter=request.user).exists()
  
            
    def get_is_saved(self,obj):
        request=self.context.get("request")
        if not request:
            return False
        if not request.user.is_authenticated:
            return False
        return SavedPost.objects.filter(user=request.user,post=obj).exists()
class PostOwnerSerializer(serializers.ModelSerializer):
    verification_badge=serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'id', 'username', 'name',  'avatar',"rating",
            "verification_badge","verification_level","reviews_count","total_posts"
            
             
        ]
        
    def get_verification_badge(self,obj):
        badge=obj.verification_badge
        return {
                "label":badge.get("label"),
                "color":badge.get("color"),
                "icon":badge.get("icon")
        }
        
        

class OwnPostListSerializer(serializers.ModelSerializer):
    is_upvoted=serializers.SerializerMethodField()
    owner=UserSerializer(read_only=True)
    is_saved=serializers.SerializerMethodField()
    images=ImageSerializer(many=True,read_only=True)
    videos=VideoSerializer(many=True,read_only=True)
    category=CategorySerializer(read_only=True)
    class Meta:
        model=Post
        fields=["id","name","description","post_type","saves_count",
                "category","images","slug",
                "views_count","upvotes","comments_count","is_upvoted","sponsored",
                "status","owner","location_display","location_lat","location_lng",
                "status","is_saved","upvotes_count","status",
                "created_at","videos"]

        
            
        
    def get_is_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return PostUpvote.objects.filter(post=obj,voter=request.user).exists()
  
            
    def get_is_saved(self,obj):
        request=self.context.get("request")
        if not request:
            return False
        if not request.user.is_authenticated:
            return False
        return SavedPost.objects.filter(user=request.user,post=obj).exists()

class PostSerializer(serializers.ModelSerializer):
    name             = serializers.CharField(required=False)
    post_type        =serializers.ChoiceField(choices=["text", "image","video"],required=True)
    description      =serializers.CharField(required=True)
    category         = serializers.CharField(required=True)
    location_lat     = serializers.CharField(required=False)
    location_lng     = serializers.CharField(required=False)
    media            = serializers.ListField(write_only=True, child=serializers.FileField(), required=False)
    media_type       = serializers.ChoiceField(choices=["photo","text","video"], write_only=True, required=False)
    location_display=serializers.CharField(required=False)
    owner      = PostOwnerSerializer(read_only=True)
    images     = ImageSerializer(many=True, read_only=True)
    videos     = VideoSerializer(many=True, read_only=True)
    is_upvoted = serializers.SerializerMethodField()
    is_saved=serializers.SerializerMethodField()

    class Meta:
        model  = Post
        fields = [
            "id", "name", "description","post_type","saves_count",
            "category", "owner", "images", "slug", "videos", "media", "created_at",
            "views_count", "location_display", "location_lat", "is_upvoted",
            "location_lng", "status", "upvotes_count", "comments_count",
            "sponsored", "media_type","is_saved"
        ]

    def get_is_upvoted(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return PostUpvote.objects.filter(post=obj, voter=request.user).exists()
    
    def get_is_saved(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return SavedPost.objects.filter(post=obj, user=request.user).exists()
    
    def to_representation(self,instance):
        data=super().to_representation(instance)
        data ["category"]= {
            "id":instance.category_id,
            "name":instance.category.name,
            
        }
        return data
    def validate(self, data):
        media      = data.get("media", [])
        media_type = data.get("media_type")
        request    = self.context.get("request")

        if media_type == "photo" and len(media) > 10:
            raise serializers.ValidationError({"media": "10 images allowed"})
        if media_type == "video" and len(media) > 10:
            raise serializers.ValidationError({"media": "Only 1 video allowed"})

        # Only validate fields that are actually being sent (safe for PATCH)
        if "name" in data and not data["name"].strip():
            raise serializers.ValidationError("Name is required")
      
        if "description" in data and not data["description"].strip():
            raise serializers.ValidationError("Description is required")
        if "category" in data and not data["category"].strip():
            raise serializers.ValidationError("Category is required")
        if "location_display" in data and not data["location_display"].strip():
            raise serializers.ValidationError("Location is required")

        # Only set owner on create, not update
        if not self.instance:
            data["owner"] = request.user

        return data

    def create(self, validated_data):
        media_files = validated_data.pop("media", [])
        media_type  = validated_data.pop("media_type", None)
        user        = validated_data["owner"]
        category_id = validated_data.pop("category")

        category = Category.objects.get(id=category_id)
        post  = Post.objects.create(category=category, **validated_data)

        if media_type == "video":
            for index, file in enumerate(media_files):
                PostVideo.objects.create(
                    owner=user, post=post, video=file, is_cover=(index == 0)
                )
        elif media_type == "photo":
            for index, file in enumerate(media_files):
                PostImage.objects.create(
                    owner=user, post=post, image=file, is_cover=(index == 0)
                )

        return post

    def update(self, instance, validated_data):
        media_files = validated_data.pop("media", [])
        media_type  = validated_data.pop("media_type", None)
        category_id = validated_data.pop("category", None)

        if category_id:
            instance.category = Category.objects.get(id=category_id)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Only append new media if provided , existing media is untouched
        if media_files and media_type == "video":
            for index, file in enumerate(media_files):
                PostVideo.objects.create(
                    owner=instance.owner, post=instance, video=file, is_cover=(index == 0)
                )
        elif media_files and media_type == "photo":
            for index, file in enumerate(media_files):
                PostImage.objects.create(
                    owner=instance.owner, post=instance, image=file, is_cover=(index == 0)
                )

        return instance
class RepliedToSerializer(serializers.ModelSerializer):
    class Meta:
        model=Comment
        fields=["id","body"]
class CommentSerializer(serializers.ModelSerializer):
    reply_to=UserSerializer(read_only=True)
    author=UserSerializer(read_only=True)
    has_upvoted=serializers.SerializerMethodField()
    has_downvoted=serializers.SerializerMethodField()
    replied_to=RepliedToSerializer(read_only=True)
    class Meta:
        model=Comment
        fields=["id","post_id","author","body","reply_to","has_upvoted","has_downvoted","replied_to",
                "upvotes_count","downvotes_count","replies_count","created_at","is_deleted","is_edited"]
    def get_has_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return CommentUpvote.objects.filter(owner=request.user,comment=obj).exists()
    def get_has_downvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return CommentDownvote.objects.filter(owner=request.user,comment=obj).exists()


#edit comment
class CommentEditSerializer(serializers.Serializer):
    body=serializers.CharField(required=True)
    
    class Meta:
        model=Comment
        fields=["id","body","parent"]
    def validate_body(self,value):
        if not value:
            raise serializers.ValidationError("body is required")
        sanitize_plain(value)
        return value
    def update_comment(self):
        comment = self.context.get('comment')
        name = self.validated_data.get('name')
        body = self.validated_data.get('body')
        comment.body=body
        comment.is_edited=True
        comment.save()
        return comment
class CommentCreateSerializer(serializers.Serializer):
    body=serializers.CharField(required=True)
    
    class Meta:
        model=Comment
        fields=["id","body","parent"]
    def validate_body(self,value):
        sanitize_plain(value)
        return value
    def create(self,validated_data):
        request=self.context.get("request")
        post=self.context.get("post")
        user=request.user
        comment=Comment.objects.create(author=user,post=post,body=validated_data.get("body"),parent=validated_data.get("parent"))
        return comment



class PostReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostReport
        fields = ["id", "reason", "description", "status", "action_taken", "created_at"]
        read_only_fields = ["id", "status", "action_taken", "created_at"]

    def validate(self, data):
        if data.get("reason") == "Other" and not data.get("description"):
            raise serializers.ValidationError({
                "description": "Required when reason is 'other'"
            })
        reason =data.get("reason")
        description=data.get("description")
        reason=sanitize_plain(reason)
        data['reason']=sanitize_plain(reason)
        data["description"]=sanitize_plain(description)
        return data
    
class SavedPostSerializer(serializers.ModelSerializer):
    post=PostListSerializer(read_only=True)
    
    class Meta:
        model=SavedPost
        fields=["id","post","created_at"]


class ReviewSerializer(serializers.ModelSerializer):
    comment=serializers.CharField(required=True)
    reviewer=UserSerializer(read_only=True)
    rating=serializers.SerializerMethodField()

    class Meta:
        model=Review
        fields=["id","reviewer","rating","comment","created_at"]
     
        
    def get_rating(self,obj):
        user=obj.reviewer
        return user.rating
    
    
    
    
    
    
    
