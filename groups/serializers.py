from .models import (Community,Membership,CommunityCategoryPost,CommunityPost,
                     CommunityPostReport,CommunityPostImage,CommunityPostVideo,CommunityPostUpvote,
                     CommunityPostComment,CommunityCommentUpvote,CommunityCommentDownvote,
                     CommunityJoinRequest,CommunitySavedPost,CommunityInvites)
from feed.models import SavedPost

from rest_framework import serializers

from django.contrib.auth import get_user_model
User=get_user_model()
from feed.serializers import UserSerializer,PostOwnerSerializer
from feed.sanitize import sanitize_plain
import filetype
from PIL import Image

class CommunityInfoSerializer(serializers.ModelSerializer):
    cover_image=serializers.SerializerMethodField()
    class Meta:
        model=Community
        fields=["id","name","description","cover_image","rules","members_count"]
    def get_cover_image(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if obj.cover_image:
            return request.build_absolute_uri(obj.cover_image.url) 
        return None
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model=CommunityCategoryPost
        fields=["id","name","slug","icon","description","order"]
        

        
class SearchUsersForRoleAssignmentSerializer(serializers.ModelSerializer):
    role=serializers.SerializerMethodField()
    is_member=serializers.SerializerMethodField()
    
    class Meta:
        model=User
        fields=["id","username","role","is_member"]
    def get_role(self,obj):
        request=self.context.get("request")
        community=self.context.get("community")
        if not request :
            return False
        membership=Membership.objects.filter(user=obj,community=community).exists()
        if membership:
            return Membership.objects.get(user=obj,community=community).role
        else:
            return None
    def get_is_member(self,obj):
        community=self.context.get("community")
        request=self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Membership.objects.filter(user=obj,community=community).exists()
class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model=CommunityPostImage
        fields=["id","image","order"]


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model=CommunityPostVideo
        fields=["id","video","order"]
        
class PostListSerializer(serializers.ModelSerializer):
    is_upvoted=serializers.SerializerMethodField()
    owner=UserSerializer(read_only=True)
    is_saved=serializers.SerializerMethodField()
    images=ImageSerializer(many=True,read_only=True)
    videos=VideoSerializer(many=True,read_only=True)
    category=CategorySerializer(read_only=True)
    class Meta:
        model=CommunityPost
        fields=["id","name","description","post_type","saves_count",
                "category","images","slug",
                "views_count","comments_count","is_upvoted","sponsored",
                "status","owner","location_display","location_lat","location_lng",
                "status","is_saved","upvotes_count",
                "created_at","videos"]

        
            
        
    def get_is_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return CommunityPostUpvote.objects.filter(post=obj,voter=request.user).exists()
  
    def get_is_saved(self,obj):
        request=self.context.get("request")
        if not request:
            return False
        if not request.user.is_authenticated:
            return False
        return CommunitySavedPost.objects.filter(user=request.user,post=obj).exists()
    
    
class PostSerializer(serializers.ModelSerializer):
    name             = serializers.CharField(required=True)
    description      = serializers.CharField(required=True)
    category         = serializers.CharField(required=True)
    location_display = serializers.CharField(required=False)
    location_lat     = serializers.CharField(required=False)
    location_lng     = serializers.CharField(required=False)
    media            = serializers.ListField(write_only=True, child=serializers.FileField(), required=False)
    media_type       = serializers.ChoiceField(choices=["photo", "video","text"], write_only=True, required=False)
    post_type        =serializers.ChoiceField(choices=["text", "image","video"],required=True)
    owner      = PostOwnerSerializer(read_only=True)
    images     = ImageSerializer(many=True, read_only=True)
    videos     = VideoSerializer(many=True, read_only=True)
    is_upvoted = serializers.SerializerMethodField()
    is_saved=serializers.SerializerMethodField()

    class Meta:
        model  = CommunityPost
        fields = [
            "id", "name", "post_type", "description",
            "category", "owner", "images", "slug", "videos", "media", "created_at",
            "views_count", "location_display", "location_lat", "is_upvoted",
            "location_lng", "status", "upvotes_count", "comments_count",
            "sponsored", "media_type","is_saved","saves_count"
        ]

    def get_is_upvoted(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return CommunityPostUpvote.objects.filter(post=obj, voter=request.user).exists()
    
    def get_is_saved(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return CommunitySavedPost.objects.filter(post=obj, user=request.user).exists()
    
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
        community=self.context.get("community")
        category = CommunityCategoryPost.objects.get(id=category_id,community=community)
        post  = CommunityPost.objects.create(category=category,community=community ,**validated_data)

        if media_type == "video":
            for index, file in enumerate(media_files):
                CommunityPostVideo.objects.create(
                    owner=user, post=post, video=file, is_cover=(index == 0)
                )
        elif media_type == "photo":
            for index, file in enumerate(media_files):
                CommunityPostImage.objects.create(
                    owner=user, post=post, image=file, is_cover=(index == 0)
                )

        return post

    def update(self, instance, validated_data):
        media_files = validated_data.pop("media", [])
        media_type  = validated_data.pop("media_type", None)
        category_id = validated_data.pop("category", None)
        community=instance.community
        if category_id:
            instance.category = CommunityCategoryPost.objects.get(id=category_id,community=community)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Only append new media if provided , existing media is untouched
        if media_files and media_type == "video":
            for index, file in enumerate(media_files):
                CommunityPostVideo.objects.create(
                    owner=instance.owner, post=instance, video=file, is_cover=(index == 0)
                )
        elif media_files and media_type == "photo":
            for index, file in enumerate(media_files):
                CommunityPostImage.objects.create(
                    owner=instance.owner, post=instance, image=file, is_cover=(index == 0)
                )

        return instance
    
class RepliedToSerializer(serializers.ModelSerializer):
    class Meta:
        model=CommunityPostComment
        fields=["id","body"]

class CommentSerializer(serializers.ModelSerializer):
    reply_to=UserSerializer(read_only=True)
    author=UserSerializer(read_only=True)
    has_upvoted=serializers.SerializerMethodField()
    has_downvoted=serializers.SerializerMethodField()
    replied_to=RepliedToSerializer(read_only=True)
    class Meta:
        model=CommunityPostComment
        fields=["id","post_id","author","body","reply_to","has_upvoted","has_downvoted","replied_to",
                "upvotes_count","downvotes_count","replies_count","created_at","is_deleted","is_edited"]
    def get_has_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return CommunityCommentUpvote.objects.filter(owner=request.user,comment=obj).exists()
    def get_has_downvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return CommunityCommentDownvote.objects.filter(owner=request.user,comment=obj).exists()


class CommentEditSerializer(serializers.Serializer):
    body=serializers.CharField(required=True)
    
    class Meta:
        model=CommunityPostComment
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
        model=CommunityPostComment
        fields=["id","body","parent"]
    def validate_body(self,value):
        sanitize_plain(value)
        return value
    def create(self,validated_data):
        request=self.context.get("request")
        post=self.context.get("post")
        user=request.user
        comment=CommunityPostComment.objects.create(author=user,post=post,body=validated_data.get("body"),parent=validated_data.get("parent"))
        return comment

class PostReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityPostReport
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
    

class AddMembersSerializer(serializers.Serializer):
    usernames = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,        # at least 1 username required
        max_length=100       # cap bulk adds
    )

    def validate_usernames(self, usernames):
        # Fetch all users that exist
        found_users = User.objects.filter(username__in=usernames)
        found_names = set(found_users.values_list('username', flat=True))

        # Report any that don't exist
        missing = set(usernames) - found_names
        if missing:
            raise serializers.ValidationError(
                f"Users not found: {', '.join(missing)}"
            )

        return found_users 
    
class SavedPostSerializer(serializers.ModelSerializer):
    post=PostListSerializer(read_only=True)
    
    class Meta:
        model=CommunitySavedPost
        fields=["id","post","created_at"]
        
        
class GroupMiniSerializer(serializers.ModelSerializer):
    role=serializers.SerializerMethodField()
    is_member=serializers.SerializerMethodField()
    
    class Meta:
        model=Community
        fields=["id","name","slug","description","cover_image","privacy","members_count","role","is_member","rules"]
    def get_role(self,obj):
        request=self.context.get("request")
        if not request :
            return False
        membership=obj.memberships.filter(user=request.user).exists()
        if membership:
            
            return obj.memberships.get(user=request.user).role
        else:
            return None
    def get_is_member(self,obj):
        request=self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.memberships.filter(user=request.user).exists()
    


class CreateGroupSerializer(serializers.ModelSerializer):
    name=serializers.CharField(required=True)
    description=serializers.CharField(required=True)
    cover_image=serializers.FileField(required=False)
    privacy=serializers.CharField(required=False)
    rules=serializers.JSONField()
    class Meta:
        model=Community
        fields=["id","name","cover_image","privacy","rules","description"]
        
    def validate_name(self,value):
        return sanitize_plain(value)
    def validate_description(self,value):
        return sanitize_plain(value)
    def validate_cover_image(self, value):
          
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Avatar too large. Max 5MB.")

    # detect from actual bytes, not client headers
        kind = filetype.guess(value.read(2048))
        value.seek(0)
        if kind is None or kind.mime not in ['image/jpeg', 'image/png', 'image/webp']:
            raise serializers.ValidationError("Invalid file. Upload a JPEG, PNG, or WebP image.")

    # verify it's not corrupt
        try:
            img = Image.open(value)
            img.verify()
            value.seek(0)
        except Exception as e:
            raise serializers.ValidationError("Uploaded file is not a valid image.")

        return value
    def _compress(self, image_file):
        img = Image.open(image_file).convert('RGB')  # convert PNG/WebP to RGB
        img.thumbnail((400, 400))  # resize in place, keeps aspect ratio

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        filename = image_file.name.rsplit('.', 1)[0] + '.jpg'

        return InMemoryUploadedFile(
            output,
            'ImageField',
            filename,
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
    def create(self,validated_data):
        user=self.context.get("request").user
        community=Community.objects.create(creator=user,**validated_data)
        Membership.objects.create(user=user,community=community,role="admin")
        return community
    def update(self,instance,validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance
class MySentRequestSerializer(serializers.ModelSerializer):
    community_slug=serializers.SerializerMethodField()
    community_name=serializers.SerializerMethodField()
    class Meta:
        model=CommunityJoinRequest
        fields=["id","community_slug","community_name","created_at"]
    def get_community_name(self,obj):
        return obj.community.name
    def get_community_slug(self,obj):
        return obj.community.slug
    
class MyInvitesSerializer(serializers.ModelSerializer):
    community_slug=serializers.SerializerMethodField()
    community_name=serializers.SerializerMethodField()
    class Meta:
        model=CommunityInvites
        fields=["id","community_slug","community_name","created_at"]
    def get_community_name(self,obj):
        return obj.community.name
    def get_community_slug(self,obj):
        return obj.community.slug
class PendingJoiRequestsSerializer(serializers.ModelSerializer):
    requester=UserSerializer(read_only=True)
    class Meta:
        model=CommunityJoinRequest
        fields=["id","requester"]
        
class PendingInvitesSerializer(serializers.ModelSerializer):
    invited=UserSerializer(read_only=True)
    class Meta:
        model=CommunityInvites
        fields=["id","invited"]