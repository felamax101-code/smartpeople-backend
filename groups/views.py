import json
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .permissions import IsCommunityAdmin,IsCommunityModerator,IsAdminOrStaff,IsCommunityMember,IsCommunityAdminOrIsCommunityModerator
from rest_framework.response import Response
from feed.pagination import CustomPagination  
from feed.geo import annotate_distance
from django.db.models import Q, Value, IntegerField, Case, When
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from .models import (Community,Membership,CommunityCategoryPost,CommunityPost,
                     CommunityPostReport,CommunityPostImage,CommunityPostVideo,CommunityPostUpvote,
                     CommunityPostComment,CommunityCommentUpvote,CommunityCommentDownvote,
                     CommunitySavedPost,CommunityInvites,CommunityJoinRequest,PostViews)


from feed.serializers import UserSerializer
from django.contrib.auth import get_user_model
User=get_user_model()
from.serializers import (
    PostListSerializer,PostSerializer,CommentSerializer,CommentEditSerializer,CommentCreateSerializer,
    PostReportSerializer,AddMembersSerializer,CategorySerializer,GroupMiniSerializer,PendingInvitesSerializer,CommunityInfoSerializer,
    PendingJoiRequestsSerializer,CreateGroupSerializer,MySentRequestSerializer,MyInvitesSerializer,SearchUsersForRoleAssignmentSerializer
)
from rest_framework.parsers import MultiPartParser

from authentication.notification_service import notify


class ProfileApprovalView(APIView):
    permission_classes=[IsAdminOrStaff]
    def get (self,request):
        "List all pending posts"
        status_filter=request.query_params.get("status","pending")
        queryset=Post.objects.filter(status=status_filter).selected_related("owner","category")
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=PostListSerializer(page,many=True,context={"request":request})
        return paginator.get_paginated_response(serailizer.data)
    
    def post (self,request,id):
        "approve or reject a post"
        try:
            post=Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return Response({
                "error":"Post requested does not exist"
            })
        action=request.data.get("action")
        reason=request.data.get("reason","")
        if action=="approve":
            post.status="approved"
            post.rejection_reason=None
            post.save()
            return Response({
                "success":True,
                "message":f"{post.name} has been approved"
            },status=200)
        elif action =="reject":
            if not reason:
                return Response({"error":"A rejection request is required"},status=400)
            post.status="rejected"
            post.rejection_reason=reason
            produvt.save()
            return Response({
                "success":True,
                "message":f"{post.name} has been rejected ;reason :{reason}"
            },status=200)
        return Response({"error":"action must be 'approv'e or 'reject'"},status=400)


class CatagoryListView(APIView):
    permission_classes=[AllowAny]
    def get (self,request,slug):
        
        categories=CommunityCategoryPost.objects.filter(is_active=True,community__slug=slug)
        serializer=CategorySerializer(categories,many=True,)
        return Response({
            "success":True,
            "data":serializer.data
        },status=200)
        
        
        
class PostListCreateView(APIView):
    permission_classes=[AllowAny]
    def get(self, request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"The requested community does not exist"
            },status=400)
            
        queryset = CommunityPost.objects.filter(community=community,status="approved",is_active=True)
        
        # --- Filtering ---
        category = request.query_params.get("category")
       
       
        
        sort = request.query_params.get("sort", "newest")
        search=request.query_params.get("search")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        
        if category:
            queryset = queryset.filter(
                Q(category__slug=category ))
      
        if search:
            queryset=queryset.filter(
                Q(name__icontains=search)| Q (description__icontains=search)
            )
        # --- Sorting ---
        if sort == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort == "most_viewed":
            queryset = queryset.order_by("-views_count")
        elif sort == "most_upvoted":
            queryset = queryset.order_by("-upvotes_count")
            radius=request.query_params.get("radius")
        elif sort =="nearest" and lat and lng:
            queryset=annotate_distance(queryset,lat,lng)
            queryset=queryset.filter(
                location_lat__isnull=False,
                location_lng__isnull=False
            )
            if radius:
                queryset=queryset.filter(distance_km__lte=float(radius))
                queryset=queryset.order_by("distance_km")
        
        
        # --- Pagination ---
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return Response({
            "success": True,
            "data": {
                "posts": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
class PendingPostListCreateView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdminOrIsCommunityModerator]
    def get(self, request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"The requested community does not exist"
            },status=400)
        self.check_object_permissions(request,community)
        queryset = CommunityPost.objects.filter(community=community,status="pending",is_active=True)
        
        # --- Filtering ---
        category = request.query_params.get("category")
      
        sort = request.query_params.get("sort", "newest")
        search=request.query_params.get("search")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        
        if category:
            queryset = queryset.filter(
                Q(category__slug=category ))
       
        if search:
            queryset=queryset.filter(
                Q(name__icontains=search)| Q (description__icontains=search)
            )
        # --- Sorting ---
        if sort == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort == "most_viewed":
            queryset = queryset.order_by("-views_count")
        elif sort == "most_upvoted":
            queryset = queryset.order_by("-upvotes_count")
            radius=request.query_params.get("radius")
        elif sort =="nearest" and lat and lng:
            queryset=annotate_distance(queryset,lat,lng)
            queryset=queryset.filter(
                location_lat__isnull=False,
                location_lng__isnull=False
            )
            if radius:
                queryset=queryset.filter(distance_km__lte=float(radius))
                queryset=queryset.order_by("distance_km")
        
        
        # --- Pagination ---
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return Response({
            "success": True,
            "data": {
                "posts": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
class RejecetedPostListCreateView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdminOrIsCommunityModerator]
    def get(self, request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"The requested community does not exist"
            },status=400)
        self.check_object_permissions(request,community)
        queryset = CommunityPost.objects.filter(community=community,status="rejected",is_active=True)
        
        # --- Filtering ---
        category = request.query_params.get("category")
       
        
        
        sort = request.query_params.get("sort", "newest")
        search=request.query_params.get("search")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        
        if category:
            queryset = queryset.filter(
                Q(category__slug=category ))
       
        if search:
            queryset=queryset.filter(
                Q(name__icontains=search)| Q (description__icontains=search)
            )
        # --- Sorting ---
        if sort == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort == "most_viewed":
            queryset = queryset.order_by("-views_count")
        elif sort == "most_upvoted":
            queryset = queryset.order_by("-upvotes_count")
            radius=request.query_params.get("radius")
        elif sort =="nearest" and lat and lng:
            queryset=annotate_distance(queryset,lat,lng)
            queryset=queryset.filter(
                location_lat__isnull=False,
                location_lng__isnull=False
            )
            if radius:
                queryset=queryset.filter(distance_km__lte=float(radius))
                queryset=queryset.order_by("distance_km")
        
        
        # --- Pagination ---
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return Response({
            "success": True,
            "data": {
                "posts": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
class PostByIdView(APIView):
        permission_classes=[AllowAny]
        def get(self,request,id):
            try:
                post=CommunityPost.objects.get(id=id)
                return Response(PostSerializer(post,context={"request": request}).data,status=200)
            except CommunityPost.DoesNotExist:
                return Response({
                "error":"Post requested does not exist"
            })


class PostCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(),IsCommunityMember()]
    def get(self,request,slug):
        try:
            post=CommunityPost.objects.get(slug=slug)
            return Response(PostSerializer(post,context={"request": request}).data,status=200)
        except CommunityPost.DoesNotExist:
            return Response({
                "error":"Post requested does not exist"
            },status=400)
    def post(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Cmmunity.DoesNotExist:
            return Response({
                "error":'The community requetsed does not exits'
            },status=400)
        self.check_object_permissions(request,community)
        serializer=PostSerializer(data=request.data,context={'request':request,"community":community})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=201)
        return Response(serializer.errors,status=400)
    def put(self,request,slug):
        user=request.user
        
        post=CommunityPost.objects.get(slug=slug)
        if user!=post.owner:
            return Response({
                "message":"You cannot edit another person's post"
            })
        serializer=PostSerializer(post,data=request.data,partial=True,context={'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=200)
        return Response(serializer.errors,status=400)
    def delete(self,request,slug):
        
        try:
            post=CommunityPost.objects.get(slug=slug)
        except CommunityPost.DoesNotExist:
            return Response({
                "error":"Post you are attempting to delete does not exist"
            },status=400)
        if post.is_active==False:
            return Response({
                 "error":"Post you are attempting to delete does not exist"
            },status=400
            )
        if request.user!=post.owner:
            return Response(
                {
                    "error":"You cannot delete another person's post"
                },status=400
            )
        post.is_active=False
        post.save()
        return Response({
            "message":"Deleted successfully"
        },status=200)
        
        
class JoinCommunityView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        slug=request.data.get("slug")
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"The community requested does not exist"
            },status=400)
        
        already_memmber=Membership.objects.filter(user=request.user,community=community).first()
        if already_memmber:
            already_memmber.delete()
            return Response({
                "message":"success"
            },status=200)
        else:
            Membership.objects.create(user=request.user,community=community)
            notify(
            recipient=community.creator,
            notification_type="new_group_member",
            title="New member in your community",
            body=f"@{request.user.username} joined {community.name} :total members:{community.members_count}",
            data={"slug": community.slug},
            send_push=True,
        )
            return Response({
                "message":"success"
            },status=200)
            
class CommentCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    def get(self,request,slug):
        post=CommunityPost.objects.get(slug=slug,is_active=True)
        if not post:
            return Response({
                "message":"The post you are referring to no longer exist"
            },status=400)
        comments=post.community_comments.filter(parent=None,is_active=True)
        paginator = CustomPagination()
        page = paginator.paginate_queryset(comments, request)
        serializer=CommentSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "comments": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
    def post(self,request,slug):
        post=CommunityPost.objects.get(slug=slug,is_active=True)
        if not post:
            
            return Response({
                "message":"The post you are trying to comment on does not exist"
            },status=400)
        serializer=CommentCreateSerializer(data=request.data,context={"request":request,"post":post})
        if serializer.is_valid():
            comment=serializer.save()
            return Response(serializer.data,status=201)
        return Response({
            "error":serializer.errors
        },status=400)
    def put(self,request,id):
        comment=CommunityPostComment.objects.get(id=id,author=request.user)
        if not comment:
            return Response({
                "message":"The comment you are trying to edit on does not exist"
            },status=400)
        serializer=CommentEditSerializer(data=request.data,context={"request":request,"comment":comment})
        if serializer.is_valid():
            comment=serializer.update_comment()
            return Response({
                
                "data":CommentSerializer(comment,context={"request": request}).data},status=201)
        return Response({
            "error":serializer.errors
        },status=400)
    def delete(self,request,id):
        comment=CommunityPostComment.objects.get(id=id,author=request.user)
        if not comment:
            return Response({
                "message":"The comment you are trying to delete on does not exist"
            },status=400)
        if comment.is_deleted:
            return Response({
                "message":"The comment you are trying to delete on does not exist"
            },status=400)
        comment.is_deleted=True
        comment.is_deleted=True
        comment.deleted_body=comment.body
        comment.body="[Deleted]"
        comment.save()
        return Response({
            "is_deleted":True
        },status=200)



class CommentReplyView(APIView):
    """Create a reply to a comment or reply"""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, comment_id):
        try:
            # always find the top-level parent
            comment = CommunityPostComment.objects.get(id=comment_id, post__slug=slug)
        except CommunityPostComment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        body = request.data.get("body", "").strip()
        reply_to_id = request.data.get("reply_to_id")  # optional - who they're replying to

        if not body:
            return Response({"error": "Reply body is required"}, status=400)

        if len(body) > 2000:
            return Response({"error": "Reply too long"}, status=400)

        # if comment is itself a reply, parent is its parent (keep flat)
        # if comment is top-level, parent is the comment itself
        parent = comment.parent if comment.parent else comment
        reply_to=User.objects.get(id=reply_to_id)
        reply = CommunityPostComment.objects.create(
            post=comment.post,
            author=request.user,
            body=body,
            parent=parent,
            reply_to=reply_to,
        )

        serializer = CommentSerializer(reply, context={"request": request})
        return Response(serializer.data, status=200)


class CommentRepliesView(APIView):
    """Get replies for a comment — paginated, max 100 per load"""
    permission_classes = [AllowAny]

    def get(self, request, slug, comment_id):
        try:
            comment = CommunityPostComment.objects.get(id=comment_id, post__slug=slug)
        except CommunityPostComment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        # fetch direct replies, flat list
        replies = CommunityPostComment.objects.filter(
            parent=comment,
        ).select_related(
            "author",
            "reply_to"  # for @mention display
        ).order_by("created_at")

        paginator = CustomPagination()
        paginator.page_size = 100  # 100 replies per load
        page = paginator.paginate_queryset(replies, request)
        serializer = CommentSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class CommentVoteView(APIView):
    """Upvote or downvote a comment/reply"""
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        vote_type = request.data.get("vote")  # "up" or "down"

        if vote_type not in ("up", "down"):
            return Response({"error": "vote must be 'up' or 'down'"}, status=400)

        try:
            comment = CommunityPostComment.objects.get(id=comment_id)
        except CommunityPostComment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        if vote_type == "up":
            existing = CommunityCommentUpvote.objects.filter(owner=request.user, comment=comment)
            if existing.exists():
                existing.delete()
                return Response({"voted": False, "type": "up"}, status=200)
            # remove downvote if exists
            CommunityCommentDownvote.objects.filter(owner=request.user, comment=comment).delete()
            CommunityCommentUpvote.objects.create(owner=request.user, comment=comment)
            return Response({"voted": True, "type": "up"}, status=200)

        else:
            existing = CommunityCommentDownvote.objects.filter(owner=request.user, comment=comment)
            if existing.exists():
                existing.delete()
                return Response({"voted": False, "type": "down"}, status=200)
            # remove upvote if exists
            CommunityCommentUpvote.objects.filter(owner=request.user, comment=comment).delete()
            CommunityCommentDownvote.objects.create(owner=request.user, comment=comment)
            return Response({"voted": True, "type": "down"}, status=200)




class PostUpvoteView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,slug):
        user=request.user
        post=CommunityPost.objects.get(slug=slug)
        like=CommunityPostUpvote.objects.filter(post=post,voter=user).exists()
        if like:
            CommunityPostUpvote.objects.filter(post=post,voter=user).delete()
            upvoted=False
        else :
            like=CommunityPostUpvote.objects.create(post=post,voter=user)
            upvoted=True
        return Response({
            "upvoted":upvoted,
            "likes_count":post.upvotes_count
        },status=200)
        
        



from feed.sanitize import sanitize_plain
class CommmentReportView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,id):
        comment=CommunityPostComment.objects.get(id=id)
        reason=request.get("reason")
        if not comment:
            return Response({
                "message":"The comment you are attempting to delete does not exist"
            },status=400)
        comment.is_reported=True
        comment.reporter=request.user
        reason=sanitize(reason)
        comment.report_reason=reason
        comment.save()
        return Response({
            "message":"Report submitted"
        })
        
class SavedPostView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        saved=CommunitySavedPost.objects.filter(user=request.user).select_related("post")
        paginator=CustomPagination()
        page=paginator.paginate_queryset(saved,request)
        serializer=SavedPostSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "posts": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
    def post(self,request,slug):
        try:
            post=CommunityPost.objects.get(slug=slug)
        except CommunityPost.DoesNotExist:
            return Response ({"error":"Post not found ,it may have been deleted"},status=400)
        #toggle key
        saved=CommunitySavedPost.objects.filter(user=request.user,post=post)
        if saved.exists():
            saved.delete()
            return Response({
                "saved":False,"message":"removed from saved list"
            },status=200)
        CommunitySavedPost.objects.create(user=request.user,post=post)
        return Response({
                "saved":True,"message":"saved to saved list"
            },status=200)
    
    def delete(self,request):
        slug=request.data.get("slug")
        try:
            post=CommunitySavedPost.objects.get(slug=slug)
            saved=CommunitySavedPost.get(post=post,user=request.user)
            saved.delete()
            return Response({
                "message":"Deleted succesfully"
            },status=200)
        except Exception:
            return Response({"error":"Request failed"},status=400)
        

class PostReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            target = Post.objects.get(id=id)
        except User.DoesNotExist:
            return Response({"error": "post not found"}, status=404)
        serializer = PostReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        result = submit_post_report(
            reporter=request.user,
            post=target,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description")
        )

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=201)
    
    
class SearchMembersView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        query=request.query_params.get("search","").strip()
        first_letter = query[0]
        users=User.objects.exclude( Q(memberships__community=community)).annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=query, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=query, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('-relevance', 'username').distinct()[:20]  # cap results
    
        unaffected_users=[]
        for user in users:
            if not CommunityInvites.objects.filter( invited=user,community=community).exists():
                unaffected_users.append(user)
        paginator=CustomPagination()
        page=paginator.paginate_queryset(unaffected_users,request)
        serializer=UserSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "users": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)


class AddMembersView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        
        serializer = AddMembersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        users = serializer.validated_data['usernames']  # already a queryset
        community.memberships.add(*users)   # bulk add, ignores duplicates automatically

        return Response({
        'message':"success",
        'total_members': community.memberships.count()
    }, status=status.HTTP_200_OK)
        
        
        
class RemoveMemberView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug,user_id):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        if not user_id:
            return Response(
                {
                    "error":"Target user not specified"
                },status=400
            )
        try:
            user=User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                "error":"Target user undefined"
            },status=400)
        membership=Membership.objects.filter(user=user,community=community).first()
        if membership:
            membership.delete()
            return Response({
            "message":"success"
        },status=200)
        else:
            return Response({
                "error":"Membership undefined"
            },status=400)
            
        
from django.core.serializers import serialize
class GetGroupMembersView(APIView):
    permission_classes=[AllowAny,IsCommunityMember]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_object_permissions(request,community)
        queryset=User.objects.filter(
           ( Q(memberships__community=community) & Q(memberships__role="member") )
            ).order_by("-memberships__joined_at")
        query=request.query_params.get("search","").strip()
        
        
        if query:
            first_letter = query[0]
            queryset = (
        queryset.filter(
            username__icontains=query
            
        )
        .annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=query, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=query, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('-relevance', 'username')  # highest score first, then alphabetical
        .distinct()[:20]  # cap results
    )
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=UserSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "users": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)




class InviteMemberView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        userId=request.data.get("user_id")
        if not userId:
            return Response({
                "message":"provide the targeted username"
            },status=400)
        already_there = CommunityInvites.objects.filter(invited_id=userId,community=community).first()
        if already_there:
            return Response({
                "message":"You have already sent an invite to this person about this community"
            },status=400)
        else :
            CommunityInvites.objects.create(inviter=request.user,invited=User.objects.get(id=userId),community=community)
            notify(
            recipient=User.objects.get(id=userId),
            notification_type="group_invite",
            title="Group invite",
            body=f"@{request.user.username} invited you to {community.name}",
            data={"slug": community.slug},
            send_push=True,
        )
        return Response({
            "message":"success"
        },status=200)
    def delete(self,request,slug,invite_id):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        if not invite_id:
            return Response({
                "message":"provide the targeted invite"
            },status=400)
        there=CommunityInvites.objects.filter(id=invite_id,community=community).first()
        if not there:
            return Response({
                "error":"You haven't sent any invite to this person concerning this community"
            },status=400)
        there.delete()
        return Response({
            "message":"Success"
        },status=200)
        
        
class AcceptInviteView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,id):
        try:
            invite=CommunityInvites.objects.filter(id=id).first()
        except CommunityInvites.DoesNotExist:
            return Response({
                "error":'error'
            },status=400)
        invite.status="accepted"
        invite.save()
        Membership.objects.create(
            community=invite.community,
            user=request.user
        )
        notify(
            recipient=invite.inviter,
            notification_type="accepted_group_invite",
            title="Group invite acceptance",
            body=f"@{request.user.username} accepted to join {invite.community.name}",
            data={"slug": invite.community.slug},
            send_push=True,
        )
        return Response({
            "message":"success"
        },status=200)
    def delete(self,request,id):
        try:
            invite=CommunityInvites.objects.filter(id=id).first()
        except CommunityInvites.DoesNotExist:
            return Response({
                "error":'error'
            },status=400)
        invite.delete()
        return Response({
            "message":"success"
        },status=200)
        
class ViewJoinRequests(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        queryset=CommunityJoinRequest.objects.filter(community=community,status="pending")
        search=request.query_params.get("search").strip()
        
        if search:
            first_letter = search[0]
            queryset = (
        queryset.filter(
            username__icontains=query
            
        )
        .annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=query, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=query, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('-relevance', 'username')  # highest score first, then alphabetical
        .distinct()[:20]  # cap results
    )
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=PendingJoiRequestsSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "join_requests": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)

class ViewPendingInvites(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        queryset=CommunityInvites.objects.filter(community=community,status="pending")
        search=request.query_params.get("search").strip()
        
        if search:
            first_letter = search[0]
            queryset = (
        queryset.filter(
            username__icontains=query
            
        )
        .annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=query, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=query, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('-relevance', 'username')  # highest score first, then alphabetical
        .distinct()[:20]  # cap results
    )
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=PendingInvitesSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "pending_invites": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
class ApproveJoinRequestsView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug,request_id):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        if not request_id:
            return Response({
                "message":"provide the targeted request"
            },status=400)
        try:
            request=CommunityJoinRequest.objects.get(id=request_id)
        except CommunityJoinRequest.DoesNotExist:
            return Response(
            {'detail': 'The target user has not requested to join group'},
            status=400
        )
        
        request.status="accepted"
        there.save()
        notify(
            recipient=request.requester,
            notification_type="group_request_accepted",
            title="Group requested accepted",
            body=f"Your request to join  {community.name} was accepted",
            data={"slug": community.slug},
            send_push=True,
        )
        return Response({
            "message":"success"
        },status=200)
    def delete(self,request,slug,request_id):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        if not request_id:
            return Response({
                "message":"provide the targeted request"
            },status=400)
        try:
            request=CommunityJoinRequest.objects.get(id=request_id)
        except CommunityJoinRequest.DoesNotExist:
            return Response(
            {'detail': 'The target user has not requested to join group'},
            status=400
        )
        request.delete()
        return Response(
            status=204
        )
        
            
        
        
        



        
#get user communities
class UserCommunitiesView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        paginator=CustomPagination()
        communities=Community.objects.filter(memberships__user=request.user).order_by("-memberships__joined_at")
        page=paginator.paginate_queryset(communities,request)
        serializer=GroupMiniSerializer(page,many=True,context={"request":request})
        return Response({
            "data":{
                "groups":serializer.data,
                "pagination":{
                    "has_next":paginator.page.has_next(),
                }}
            },status=200
        )
import random
from django.db.models import Max
class UserCommunitySuggestionaView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        ids=list(Community.objects.exclude(memberships__user=request.user).values_list("id",flat=True))
        if not ids:
            return Response([],status=200)
        random_ids=random.sample(ids,min(5,len(ids)))
        already_requested_ids=set(
            CommunityJoinRequest.objects.filter(requester=request.user,community_id__in=random_ids).values_list("community_id",flat=True))
        final_ids=[cid for cid in  random_ids if cid not in already_requested_ids]
        communities=Community.objects.filter(id__in=final_ids)
        serializer=GroupMiniSerializer(communities,many=True,context={"request":request})
        return Response(serializer.data,status=200)
    
        
class CreateGroupView(APIView):
    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser]
    def post(self,request):
        serializer=CreateGroupSerializer(data=request.data,context={"request":request})
        if serializer.is_valid():
            c=serializer.save()
            return Response({
                "slug":c.slug
            },status=200)
        return Response(serializer.errors,status=400)
    def put(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"corresponding coomunity was not found"
            },status=400)
        serializer=CreateGroupSerializer(community,data=request.data,partial=True,context={"request":request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message":"success"
            },status=200)
        return Response(serializer.errors,status=400)
    
class UserInfoOnCommunity(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"corresponding coomunity was not found"
            },status=400)
        serializer=GroupMiniSerializer(community,context={"request":request})
        return Response(serializer.data,status=200)
        
class GetAdimnModerator(APIView):
    permission_classes=[IsAuthenticated,IsCommunityMember]
    def get(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"corresponding coomunity was not found"
            },status=400)
        self.check_object_permissions(request,community)
        queryset=User.objects.filter(Q(memberships__community=community) & (Q(memberships__role="admin")| Q(memberships__role="moderator")))
        search=request.query_params.get("search").strip()
        
        if search:
            first_letter = search[0]
            queryset = (
        queryset.filter(
            username__icontains=query
            
        )
        .annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=query, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=query, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('-relevance', 'username')  # highest score first, then alphabetical
        .distinct()[:20]  # cap results
    )
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=UserSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "users": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
class CommunityInfoView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityMember]
    def get(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"corresponding coomunity was not found"
            },status=400)
        self.check_object_permissions(request,community)
        serializer=CommunityInfoSerializer(community,context={"request": request})
        return Response(serializer.data,status=200)
        
class CommunityRules(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,slug):
        try:
            community=Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response({
                "error":"corresponding coomunity was not found"
            },status=400)
        return Response(serialize("json",community.rules),status=200)
    
class MySentRequestsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        queryset=CommunityJoinRequest.objects.filter(requester=request.user,status="pending").order_by("-created_at")
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=MySentRequestSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "requests": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
class MyInvitesView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        queryset=CommunityInvites.objects.filter(invited=request.user,status="pending").order_by("-created_at")
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=MyInvitesSerializer(page,many=True,context={"request":request})
        return Response({
            "success": True,
            "data": {
                "invites": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)


class SearchUsersForRoleAssignment(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        # queryset=User.objects.filter(
        #     Q(memberships__community=community) & Q(memberships__role="member")
        # ).order_by("-created_at")
        queryset=User.objects.exclude(
           (Q (memberships__community=community) & 
           Q (memberships__role__in=["admin","moderator"]))
        ).order_by("-created_at")
        search=request.query_params.get("search").strip()
        
        if search:
            first_letter = search[0]
            queryset = (
        queryset.filter(
            username__icontains=search
            
        )
        .annotate(
            relevance=Case(
                # Score 4 — exact username match
                When(username__iexact=search, then=Value(4)),

                # Score 3 — starts with full query string
                When(username__istartswith=search, then=Value(3)),
                

                # Score 2 — starts with just the first letter typed
                When(username__istartswith=first_letter, then=Value(2)),
                
                # Score 1 — query appears somewhere (contains)
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('-relevance', 'username')  # highest score first, then alphabetical
        .distinct()[:20]  # cap results
    )
        uninvited=[]
        for user in queryset:
            if not CommunityInvites.objects.filter( invited=user,community=community).exists():
                uninvited.append(user)
        paginator=CustomPagination()
        page=paginator.paginate_queryset(uninvited,request)
        serializer=SearchUsersForRoleAssignmentSerializer(page,many=True,context={"request":request,"community":community})
        return Response({
            "success": True,
            "data": {
                "users": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.get_page_size(request),
                    "total": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
class MakeUserAdminOrModerator(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        user_id=request.data.get("user_id")
        role=request.data.get("role").strip()
        if not user_id or not role:
            return Response(
                {
                    "error":"Specify both target user and the role"
                },status=400
            )
        try:
            user=User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
            {'detail': 'user referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        membership=Membership.objects.filter(user=user,community=community).first()
        if membership:
            membership.role=role
            membership.save()
            return Response(
                {
                    "message":"success"
                },status=200
            )
        else :
            return Response(
            {'detail': 'user referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        
class GetAsignedRoles(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdminOrIsCommunityModerator]
    def get(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_object_permissions(request,community)
            
        membership=Membership.objects.filter(user=request.user,community=community).exists()
        if membership:
            return Response({
                "rules":memberhip.rules
            },status=200)
        else:
            return Response(
                {
                    "error":"The associated user was not found in this queried community"
                },status=400
            )
class AsignRoleToAModerator(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
class ApprovePostView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdminOrIsCommunityModerator]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_object_permissions(request,community)
        post_slug=request.data.get("post_slug")
        try:
            post=CommunityPost.objects.filter(community=community,slug=post_slug).first()
        except CommunityPost.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
            
        post.status="approved"
        post.save()
        return Response({
            "message":"success"
        },status=200)


class RejectPostView(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdminOrIsCommunityModerator]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_object_permissions(request,community)
        post_slug=request.data.get("post_slug")
        reason=request.data.get("reason")
        try:
            post=CommunityPost.objects.filter(community=community,slug=post_slug).first()
        except CommunityPost.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
            
        post.status="approved"
        post.rejection_reason=reason
        post.save()
        return Response({
            "message":"success"
        },status=200)

class RequestToJoinAprivateCommunity(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        existing=CommunityJoinRequest.objects.filter(community=community,requester=request.user).first()
        if existing:
            existing.delete()
            return Response({
                "message":"success"
            },status=200)
        else:
            CommunityJoinRequest.objects.create(community=community,requester=request.user)
            admins=User.objects.filter(
                (Q(memberships__community=community) & Q(memberships__role="admin"))
            )
            for user in admins:
                notify(
            recipient=user,
            notification_type="group_join_request",
            title="Request to join your community",
            body=f"@{user.username} requested to join {community.name}",
            data={"slug": community.slug},
            send_push=True,
        )
            return Response({
                "message":"success"
            },status=200)
    def delete(self,request,id):
        try:
            request=CommunityJoinRequest.objects.filter(id=id)
        except CommunityJoinRequest.DoesNotExist:
            return Response({
                "error":"Error"
            },status=400)
        request.delete()
        return Response({
            "message":"success"
        },status=200)
            
class AddRemoveCategory(APIView):
    permission_classes=[IsAuthenticated,IsCommunityAdmin]
    def post(self,request,slug):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_object_permissions(request,community)
        category_name=request.data.get("category")
        if not category_name or category_name and not category_name.strip():
            return Response({
                "error":"Provide a category name"
            },status=400)
    
        category=CommunityCategoryPost.objects.filter(name__iexact=category_name.casefold(),community=community).first()
        if category:
            return Response({
                "error":"Category with this name already exist in this community"
            },status=400)
        else:
            CommunityCategoryPost.objects.create(name=category_name.capitalize(),community=community)
            return Response({
            "message":"success"
        },status=200)
    def delete(self,request,slug,id):
        try:
            community = Community.objects.get(slug=slug)
        except Community.DoesNotExist:
            return Response(
            {'detail': 'Community referred not found or you do not have permission.'},
            status=status.HTTP_404_NOT_FOUND
        )
        category=CommunityCategoryPost.objects.filter(id=id,community=community).first()
        if not category:
            return Response({
                "error":"category not found"
            },status=400)
        category.delete()
        return Response(status=200)

class PostViewsView(APIView):
    permission_classes = [AllowAny]
    def post(self,request,slug):
        post = get_object_or_404(CommunityPost,slug=slug) 
        user=  request.user
        if request.user.is_authenticated:
            PostViews.objects.get_or_create(post=post,user=user)
        return Response(status=200)
class ViewsCount(APIView):
    permission_classes = [AllowAny]
    def get(self,request,slug):
        post = get_object_or_404(CommunityPost,slug=slug) 
        if post:
            return Response ({
                "views_count":post.views_count
                },status=200)