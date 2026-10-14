from rest_framework import serializers
from .sanitize import sanitize_plain,sanitize_post_content
from .upload import upload_image,upload_video
from .models import ( Post,PostImage,Category,Comment,SavedPost,PostVideo,Review,
                     CommentUpvote,PostUpvote,CommentDownvote,PostReport,PostSound,Sound)
from django.contrib.auth import get_user_model
User=get_user_model()
import os
from .audio_utils import get_duration
from django.utils import timezone
from functools import partial
from django.db import transaction
from .utils import save_temp_upload,user_can_use_sound
from .tasks import transcode_and_attach_video
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
            'id', 'username', 'avatar',
            "verification_badge",
            
             
        ]
        
    def get_verification_badge(self,obj):
        badge=obj.verification_badge
        return {
                "label":badge.get("label"),
                "color":badge.get("color"),
                "icon":badge.get("icon")
        }
        

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
MAX_SOUND_SIZE = 20 * 1024 * 1024   # 20 MB
MIN_SOUND_SECONDS = 1
MAX_SOUND_SECONDS = 10 * 60         # 10 minutes


class SoundUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sound
        fields = ["id", "title", "file", "duration"]
        read_only_fields = ["id", "duration"]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title is required.")
        return sanitize_plain(value)

    def validate_file(self, f):
        # cheap checks first, before reading the file
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise serializers.ValidationError(
                "Unsupported format. Use mp3, m4a, wav, ogg, flac or aac."
            )
        if f.size > MAX_SOUND_SIZE:
            raise serializers.ValidationError("File is too large (max 20 MB).")

        # mutagen reads the real content, so a renamed file is rejected here
        try:
            duration = get_duration(f)
        except Exception as e:
            raise serializers.ValidationError(e)
        finally:
            f.seek(0)  # rewind so the file can still be saved

        if duration < MIN_SOUND_SECONDS:
            raise serializers.ValidationError("Sound is too short.")
        if duration > MAX_SOUND_SECONDS:
            raise serializers.ValidationError("Sound is too long (max 10 minutes).")

        self._duration = duration
        return f

    def create(self, validated_data):
        validated_data["duration"] = self._duration
        return super().create(validated_data)
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
        fields=["id","video","order","processing_status"]
class PostListSerializer(serializers.ModelSerializer):
    is_upvoted=serializers.SerializerMethodField()
    owner=UserSerializer(read_only=True)
    sound = serializers.SerializerMethodField()
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
                "created_at","videos","sound"]

        
            
        
    def get_is_upvoted(self,obj):
        request=self.context.get("request")
        if not request:
            return None
        if not request.user.is_authenticated:
            return None
        return PostUpvote.objects.filter(post=obj,voter=request.user).exists()
    def get_sound(self, obj):
        ps = getattr(obj, "post_sound", None)
        if ps is None:
            return None
        # takedown: photo posts lose their music; videos have it baked in already
        if ps.sound.status != "active" and obj.post_type == "image":
            return None
        return PostSoundSerializer(ps).data
            
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
# serializers.py
class SoundFilterSerializer(serializers.Serializer):
    """Validates query params, so bad input returns a 400 instead of a 500."""
    q = serializers.CharField(required=False, allow_blank=True, max_length=100)
    owner = serializers.CharField(required=False, allow_blank=True, max_length=150)
    min_duration = serializers.FloatField(required=False, min_value=0)
    max_duration = serializers.FloatField(required=False, min_value=0)

    def validate(self, data):
        lo, hi = data.get("min_duration"), data.get("max_duration")
        if lo is not None and hi is not None and lo > hi:
            raise serializers.ValidationError(
                {"min_duration": "min_duration can't be greater than max_duration."}
            )
        return data


class SoundListSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username")
    preview_url = serializers.CharField(read_only=True)

    class Meta:
        model = Sound
        fields = ["id", "title", "owner", "duration", "price", "preview_url", "created_at"]
SOUND_INPUT_FIELDS = ("sound_id", "music_start", "music_volume", "keep_original_audio")
class PostSoundSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="sound.id")
    title = serializers.CharField(source="sound.title")
    creator = serializers.CharField(source="sound.owner.username")
    preview_url = serializers.CharField(source="sound.preview_url")
    # url = serializers.SerializerMethodField()

    class Meta:
        model = PostSound
        fields = ["id", "title", "creator", "preview_url",
                  "start_offset", "volume", "keep_original_audio"]
        
    # def get_url(self, obj):
    #     return obj.sound.file.url
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
    client_upload_id = serializers.UUIDField(required=False, write_only=True)
    sound_id = serializers.UUIDField(write_only=True, required=False)  
    # music_start = serializers.FloatField(write_only=True, required=False, min_value=0)
    # music_volume = serializers.FloatField(write_only=True, required=False, min_value=0, max_value=1)
    is_saved=serializers.SerializerMethodField()
    # keep_original_audio = serializers.BooleanField(write_only=True, required=False, default=True)
    sound = serializers.SerializerMethodField()
    class Meta:
        model  = Post
        fields = [
            "id", "name", "description","post_type","saves_count",
            "category", "owner", "images", "slug", "videos", "media", "created_at",
            "views_count", "location_display", "location_lat", "is_upvoted",
            "location_lng", "status", "upvotes_count", "comments_count",
            "sponsored", "media_type","is_saved","client_upload_id","sound_id","sound"
        ]
    def get_sound(self, obj):
        ps = getattr(obj, "post_sound", None)
        if ps is None:
            return None
        # takedown: photo posts lose their music; videos have it baked in already
        if ps.sound.status != "active" and obj.post_type == "image":
            return None
        return PostSoundSerializer(ps).data
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

        if media_type == "photo" and len(media) > 5:
            raise serializers.ValidationError({"media": "10 images allowed"})
        if media_type == "video" and len(media) > 1:
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
        data = self._validate_sound(data, request)
        return data
    def _pop_sound_data(self, validated_data):
        sound = validated_data.pop("sound_obj", None)
        start = validated_data.pop("music_start", 0)
        volume = validated_data.pop("music_volume", 0.5)
        keep = validated_data.pop("keep_original_audio", True)
        validated_data.pop("sound_id", None)
        if sound is None:
            return None
        return {"sound": sound, "start_offset": start,
                "volume": volume, "keep_original_audio": keep}
    def _validate_sound(self, data, request):
        sound_id = data.get("sound_id")

        if sound_id is None:
            for f in SOUND_INPUT_FIELDS:   # settings without a sound are meaningless
                data.pop(f, None)
            return data

        post_type = data.get("post_type") or (self.instance.post_type if self.instance else None)
        if post_type != "image":
            raise serializers.ValidationError({"sound_id": "Text posts can't have music."})
        if self.instance and self.instance.post_type == "video":
            raise serializers.ValidationError(
                {"sound_id": "Music can't be changed after a video is posted."}
            )

        try:
            sound = Sound.objects.get(id=sound_id, status="active")
        except Sound.DoesNotExist:
            raise serializers.ValidationError({"sound_id": "This sound is not available."})

        if not user_can_use_sound(request.user, sound):
            raise serializers.ValidationError({"sound_id": "You need a license to use this sound."})

        if sound.duration and data.get("music_start", 0) >= sound.duration:
            raise serializers.ValidationError({"music_start": "Start time is past the end of the track."})

        data["sound_obj"] = sound   # resolved object, so create() doesn't query again
        return data
    def create(self, validated_data):
        media_files = validated_data.pop("media", [])
        media_type = validated_data.pop("media_type", None)
        sound_data = self._pop_sound_data(validated_data)
        user = validated_data["owner"]
        category_id = validated_data.pop("category")

        with transaction.atomic():
            category = Category.objects.get(id=category_id)
            post = Post.objects.create(category=category, **validated_data)

            if sound_data:
                PostSound.objects.create(post=post, **sound_data)

            if media_type == "video":
                for index, file in enumerate(media_files):
                    post_video = PostVideo.objects.create(owner=user, post=post, is_cover=(index == 0))
                    tmp_path = save_temp_upload(file, post_video.id)
                    transaction.on_commit(
                        partial(transcode_and_attach_video.delay, str(post_video.id), tmp_path)
                    )
            elif media_type == "photo":
                for index, file in enumerate(media_files):
                    PostImage.objects.create(owner=user, post=post, image=file, is_cover=(index == 0))

        return post

    def update(self, instance, validated_data):
        media_files = validated_data.pop("media", [])
        media_type  = validated_data.pop("media_type", None)
        category_id = validated_data.pop("category", None)
        sound_data = self._pop_sound_data(validated_data)
        if sound_data:
            PostSound.objects.update_or_create(post=instance, defaults=sound_data)
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
    #helpers

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
    body=serializers.CharField(required=True,max_length=2000)
    
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
    
    
    
    
    
    
    
