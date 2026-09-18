from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Value, IntegerField, Case, When
from authentication.models import Follow
from .models import PostViews,Post,Comment,PostUpvote,CommentDownvote,CommentUpvote,Category,Review,SavedPost,PropertyProfile,ListingApplication,PostReport
from .serializers import (PostSerializer,PostListSerializer,CommentSerializer,CommentCreateSerializer,
                          CategorySerializer,ReviewSerializer,OwnPostListSerializer,CommentEditSerializer,
                          PostReportSerializer,SavedPostSerializer,SearchUsersSerializer,PropertyProfileSerializer,ListingApplicationSerializer)
from feed.pagination import CustomPagination  
from feed.geo import annotate_distance
from django.db.models import Q
from django.contrib.auth import get_user_model
User=get_user_model()


class MyPropertyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = PropertyProfile.objects.get_or_create(user=request.user)
        serializer = PropertyProfileSerializer(profile)
        return Response(serializer.data)
class OtherPersonPropertyProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request,username):
        try:
            profile = PropertyProfile.objects.get(user__username=username)
        except PropertyProfile.DoesNotExist:
            return Response(status=404)
        serializer = PropertyProfileSerializer(profile)
        return Response(serializer.data)

class ListingApplicationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # enforce: no new application while one is still pending
        has_pending = ListingApplication.objects.filter(
            user=request.user, status="pending"
        ).exists()

        if has_pending:
            return Response(
                {"error": "You already have a pending application."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # block reapplying if already approved (already has posting rights)
        profile = PropertyProfile.objects.filter(user=request.user).first()
        if profile and profile.can_post_listings:
            return Response(
                {"error": "You're already approved to post listings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyListingApplicationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        application = (
            ListingApplication.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )

        can_post = PropertyProfile.objects.filter(
            user=request.user, can_post_listings=True
        ).exists()

        if not application:
            return Response({
                "has_applied": False,
                "can_post_listings": can_post,
                "application": None,
            })

        return Response({
            "has_applied": True,
            "can_post_listings": can_post,
            "application": ListingApplicationSerializer(application).data,
        })

class ProfileApprovalView(APIView):
   
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
            post.save()
            return Response({
                "success":True,
                "message":f"{post.name} has been rejected ;reason :{reason}"
            },status=200)
        return Response({"error":"action must be 'approv'e or 'reject'"},status=400)
class CatagoryListView(APIView):
    permission_classes=[AllowAny]
    def get (self,request):
        categories=Category.objects.filter(is_active=True)
        serializer=CategorySerializer(categories,many=True,)
        return Response({
            "success":True,
            "data":serializer.data
        },status=200)

class PostListCreateView(APIView):
    permission_classes=[AllowAny]
    def get(self, request):
        queryset = Post.objects.filter(status="approved",is_active=True)
        
        # --- Filtering ---
        user= request.query_params.get("user")
        category = request.query_params.get("category")
        user_id = request.query_params.get("user_id")
        sort = request.query_params.get("sort", "newest")
        search=request.query_params.get("search")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        location = request.query_params.get("location")
        house_type = request.query_params.get("house_type")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        if location:
            queryset = queryset.filter(location__icontains=location)
        if house_type:
            queryset = queryset.filter(house_type__icontains=house_type)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if user:
            queryset = queryset.filter(
                Q(owner__username=user ))
        if category:
            queryset = queryset.filter(
                Q(category__slug=category ))
        if user_id:
            queryset = queryset.filter(user__id=user_id)
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
        



class SearchUsersView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
       
        # queryset=User.objects.filter(
        #     Q(memberships__community=community) & Q(memberships__role="member")
        # ).order_by("-created_at")
        
        search=request.query_params.get("search").strip()
        queryset=User.objects.filter(
           username__icontains=search
        ).order_by("-created_at")
        if request.user.is_authenticated:
            user=request.user
            queryset=queryset.exclude(username=user.username)
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
        
        paginator=CustomPagination()
        page=paginator.paginate_queryset(queryset,request)
        serializer=SearchUsersSerializer(page,many=True ,context={"request": request})
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
class UserListCreateView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request):
        queryset = Post.objects.filter(owner=request.user,is_active=True)
        
        # --- Filtering ---
        
        category = request.query_params.get("category")
        
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        sort = request.query_params.get("sort", "newest")
        search=request.query_params.get("search")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        if category:
            queryset = queryset.filter(
                Q(category__slug=category ))
       
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
       
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
        
        
        
        # --- Pagination ---
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OwnPostListSerializer(page, many=True, context={"request": request})
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
                post=Post.objects.get(id=id)
                return Response(PostSerializer(post,context={"request": request}).data,status=200)
            except Post.DoesNotExist:
                return Response({
                "error":"Post requested does not exist"
            })

class PostCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    def get(self,request,slug):
        
        
        try:
            post=Post.objects.get(slug=slug)
            return Response(PostSerializer(post,context={"request": request}).data,status=200)
        except Post.DoesNotExist:
            return Response({
                "error":"Post requested does not exist"
            },status=400)
    def post(self,request):
        serializer=PostSerializer(data=request.data,context={'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=201)
        return Response(serializer.errors,status=400)
    def put(self,request,slug):
        user=request.user
        try:
            post=Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return Response({
                "error":"Post requested does not exist"
            },status=400)
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
            post=Post.objects.get(slug=slug)
        except Post.DoesNotExist:
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
            
        
class FollowView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,username):
        try:
            target_user=User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                "error":"The user you are trying to follow does not exist"
            },status=400)
        user=request.user
        follow=Follow.objects.filter(follower=user,following=target_user).first()
        if  not follow:
            Follow.objects.create(follower=user,following=target_user)
            following=True
        else:
            follow.delete()
            following=False
        user.refresh_from_db()
        return Response({
            "following":following,
            "followers_count":user.followers
        },status=200)
        
class CommentCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    def get(self,request,slug):
        post=Post.objects.get(slug=slug,is_active=True)
        if not post:
            return Response({
                "message":"The post you are referring to no longer exist"
            },status=400)
        comments=post.comments.filter(parent=None,is_active=True)
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
        post=Post.objects.get(slug=slug,is_active=True)
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
        comment=Comment.objects.get(id=id,author=request.user)
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
        comment=Comment.objects.get(id=id,author=request.user)
        if not comment:
            return Response({
                "message":"The comment you are trying to delete on does not exist"
            },status=400)
        if comment.is_deleted:
            return Response({
                "message":"The comment you are trying to delete on does not exist"
            },status=400)
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
            parent = Comment.objects.get(id=comment_id, post__slug=slug)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)
        replied_to_comment_id=request.data.get("replied_to_comment_id")
        replied_to_comment=None
        if replied_to_comment_id:
            try:
            #  find the actual comment being replied to
                replied_to_comment = Comment.objects.get(id=replied_to_comment_id,parent=parent, is_deleted=False)
            except Comment.DoesNotExist:
                replied_to_comment=None

        body = request.data.get("body", "").strip()
        # reply_to_id = request.data.get("reply_to_id")  # optional - who they're replying to -person

        if not body:
            return Response({"error": "Reply body is required"}, status=400)

        if len(body) > 2000:
            return Response({"error": "Reply too long"}, status=400)

        
        # reply_to=User.objects.get(id=reply_to_id)
        reply = Comment.objects.create(
            post=parent.post,
            author=request.user,
            body=body,
            parent=parent,
            replied_to=replied_to_comment,
            reply_to=replied_to_comment.author if replied_to_comment else parent.author,
        )

        serializer = CommentSerializer(reply, context={"request": request})
        return Response(serializer.data, status=201)


class CommentRepliesView(APIView):
    """Get replies for a comment — paginated, max 100 per load"""
    permission_classes = [AllowAny]

    def get(self, request, slug, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id, post__slug=slug)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        # fetch direct replies, flat list
        replies = Comment.objects.filter(
            parent=comment,
        ).select_related(
            "author",
            "reply_to" , # for @mention display user being replied to
            "replied_to",#the actul comment being replied to
        ).order_by("created_at")

        paginator = CustomPagination()
        paginator.page_size = 100  # 100 replies per load
        page = paginator.paginate_queryset(replies, request)
        serializer = CommentSerializer(page, many=True, context={"request": request})
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


class CommentVoteView(APIView):
    """Upvote or downvote a comment/reply"""
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        vote_type = request.data.get("vote")  # "up" or "down"

        if vote_type not in ("up", "down"):
            return Response({"error": "vote must be 'up' or 'down'"}, status=400)

        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        if vote_type == "up":
            existing = CommentUpvote.objects.filter(owner=request.user, comment=comment)
            if existing.exists():
                existing.delete()
                return Response({"voted": False, "type": "up"}, status=200)
            # remove downvote if exists
            CommentDownvote.objects.filter(owner=request.user, comment=comment).delete()
            CommentUpvote.objects.create(owner=request.user, comment=comment)
            return Response({"voted": True, "type": "up"}, status=200)

        else:
            existing = CommentDownvote.objects.filter(owner=request.user, comment=comment)
            if existing.exists():
                existing.delete()
                return Response({"voted": False, "type": "down"}, status=200)
            # remove upvote if exists
            CommentUpvote.objects.filter(owner=request.user, comment=comment).delete()
            CommentDownvote.objects.create(owner=request.user, comment=comment)
            return Response({"voted": True, "type": "down"}, status=200)




class PostUpvoteView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,slug):
        user=request.user
        post=Post.objects.get(slug=slug)
        like=PostUpvote.objects.filter(post=post,voter=user).exists()
        if like:
            PostUpvote.objects.filter(post=post,voter=user).delete()
            upvoted=False
        else :
            like=PostUpvote.objects.create(post=post,voter=user)
            upvoted=True
        return Response({
            "upvoted":upvoted,
            "likes_count":post.upvotes_count
        },status=200)
        
        



from feed.sanitize import sanitize_plain
class CommmentReportView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,id):
        comment=Comment.objects.get(id=id)
        reason=request.data.get("reason")
        if not comment:
            return Response({
                "message":"The comment you are attempting to delete does not exist"
            },status=400)
        comment.is_reported=True
        comment.reporter=request.user
        reason=sanitize_plain(reason)
        comment.report_reason=reason
        comment.save()
        return Response({
            "message":"Report submitted"
        })
        
class SavedPostView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        saved_ids=request.user.saved_posts.values_list("post_id",flat=True).order_by("-created_at")
        posts=Post.objects.filter(id__in=saved_ids)
        paginator=CustomPagination()
        page=paginator.paginate_queryset(posts,request)
        serializer=OwnPostListSerializer(page,many=True,context={"request":request})
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
            post=Post.objects.get(slug=slug,is_active=True,status="approved")
        except Post.DoesNotExist:
            return Response ({"error":"Post not found ,it may have been deleted"})
        #toggle key
        saved=SavedPost.objects.filter(user=request.user,post=post)
        if saved.exists():
            saved.delete()
            return Response({
                "saved":False,"message":"removed from saved list"
            })
        SavedPost.objects.create(user=request.user,post=post)
        return Response({
                "saved":True,"message":"saved to saved list"
            })
    
    def delete(self,request):
        slug=request.data.get("slug")
        try:
            post=Post.objects.get(slug=slug)
            saved=SavedPost.get(post=post,user=request.user)
            saved.delete()
            return Response({
                "message":"Deleted succesfully"
            },status=200)
        except Exception:
            return Response({"error":"Request failed"},status=400)
        

from authentication.report_service import submit_post_report


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

        try:
            PostReport.objects.create(
            reporter=request.user,
            post=target,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description")
        )
            return Response("reported", status=201)
        except Exception as e:
            print(e)
            return Response("Report failed", status=400)




        
class ReviewAPIview(APIView):
    
    permission_classes=[AllowAny]
    def get(self,request,username):
        queryset=Review.objects.filter(target__username=username).order_by("-created_at")
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ReviewSerializer(page, many=True, context={"request": request})
            return Response({
                    
            "success": True,
            "data": {
                "reviews": serializer.data,
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
        serializer = ReviewSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
        
        
    def post(self, request, username):
        try:
            target =User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # cannot review yourself
        if request.user == target:
            return Response({"error": "You cannot review yourself"}, status=400)

        rating = request.data.get("rating")
        comment = request.data.get("comment", "").strip()

        # validate rating
        if not rating or not str(rating).isdigit():
            return Response({"error": "Rating is required"}, status=400)

        rating = int(rating)
        if not 1 <= rating <= 5:
            return Response({"error": "Rating must be between 1 and 5"}, status=400)

        # check duplicate
        existing = Review.objects.filter(
            reviewer=request.user,
            target=target
        ).first()
        
        if existing:
            # update existing review
            existing.rating = rating
            existing.comment = comment
            existing.save()

            # update user's average rating
            _update_user_rating(target)

            return Response({
                "success": True,
                "message": "Review updated",
            }, status=200)

        # create new review
        Review.objects.create(
            reviewer=request.user,
            target=target,
            rating=rating,
            comment=comment,
        )

        _update_user_rating(target)
        
        
        # notify user
        from authentication.notification_service import notify
        notify(
            recipient=target,
            notification_type="new_review",
            title="New review received",
            body=f"@{request.user.username} left you a {rating}★ review",
            data={"username": request.user.username},
            send_push=True,
        )

        return Response({
            "success": True,
            "message": "Review submitted",
        }, status=201)
        
        
        
    def delete(self, request, username):
        """Delete your own review of a user"""
        try:
            target = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        deleted = Review.objects.filter(
            reviewer=request.user,
            target=target
        ).delete()

        if deleted[0] == 0:
            return Response({"error": "Review not found"}, status=404)

        _update_user_rating(target)
        return Response({"success": True}, status=200)
def _update_user_rating(user):
    """Recalculate user's average rating after any review change"""
    from django.db.models import Avg, Count
    result = Review.objects.filter(target=user).aggregate(
    avg=Avg("rating"),
    count=Count("id")
    )
    User.objects.filter(id=user.id).update(
    rating=round(result["avg"] or 0, 1),
    reviews_count=result["count"]
    )
        

        
        




class ProfileSitemapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        profiles = User.objects.only("id","username", "updated_at").order_by("-updated_at")
        data = [
            {"id": p.id, "updated_at": p.updated_at,"username":p.username}
            for p in profiles
        ]
        return Response({"success": True, "data": {"profiles": data}}, status=status.HTTP_200_OK)
        
        
        
        
        
class PostSitemapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        posts = Post.objects.only("id", "slug", "updated_at").order_by("-updated_at")
        data = [
            {"slug": p.slug, "updated_at": p.updated_at}
            for p in posts
        ]
        return Response({"success": True, "data": {"posts": data}}, status=status.HTTP_200_OK)
        
        
class PostViewsView(APIView):
    permission_classes = [AllowAny]
    def post(self,request,slug):
        post = get_object_or_404(Post,slug=slug) 
        user=  request.user
        if request.user.is_authenticated:
            PostViews.objects.get_or_create(post=post,user=user)
        return Response(status=200)
class ViewsCount(APIView):
    permission_classes = [AllowAny]
    def get(self,request,slug):
        post = get_object_or_404(Post,slug=slug) 
        if post:
            return Response ({
                "views_count":post.views_count
                },status=200)