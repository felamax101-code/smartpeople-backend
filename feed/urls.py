from django.urls import path
from .views import (PostCreateView,PostListCreateView,CommentCreateView,FollowView,
                    PostUpvoteView,CommmentReportView,
                    SavedPostView,CatagoryListView,ProfileApprovalView,ReviewAPIview,
                    CommentRepliesView,CommentReplyView,CommentVoteView,PostByIdView,UserListCreateView,
                    PostReportView,SearchUsersView,ProfileSitemapView,PostSitemapView,PostViewsView,ViewsCount,PostRepostView)


urlpatterns = [
    #admin actions
    path("admin/postts/",ProfileApprovalView.as_view(),name="admin-post-list"),
    path("admin/postts/<uuid:id>",ProfileApprovalView.as_view(),name="admin-post-action"),
    #categories
    path("categories/",CatagoryListView.as_view(),name="categories"),
    path("posts/",PostCreateView.as_view(),name="create/delete-post"),
    path("posts/edit/<str:slug>/",PostCreateView.as_view(),name="edit-post"),

    path("postbyid/<uuid:id>/",PostByIdView.as_view(),name="get-create/edit/delete-post"),

    path("post/<slug:slug>/",PostCreateView.as_view(),name="get-create/edit/delete-post"),
    path("feed/",PostListCreateView.as_view(),name="feed"),
    path("user/listings/",UserListCreateView.as_view(),name="see-own-posts"),

    ##comments
    path("post/<str:slug>/comments/",CommentCreateView.as_view(),name="create-comment"),
    path("comment/<uuid:id>/",CommentCreateView.as_view(),name=",delete,edit-comment"),
    path("comment/report/<uuid:id>/",CommmentReportView.as_view(),name="report-comment"),
    
    path("users/<str:username>/follow/",FollowView.as_view(),name="follow-another-user"),
    #gat/saved/unsave posts
    path("wishlist/",SavedPostView.as_view(),name="get/delete-saved-post"),
    path("wishlist/<slug:slug>/",SavedPostView.as_view(),name="saved/unsave-post"),
    
    #post report
    path("post/<uuid:id>/report/",PostReportView.as_view(),name="report-post"),

    
    ##upvote post
    path("post/<str:slug>/upvote/",PostUpvoteView.as_view(),name="like-post"),
    
    path("users/<str:username>/reviews/",ReviewAPIview.as_view(),name="lget-reviews"),
    path("repost/<slug:slug>/post/",PostRepostView.as_view(),name="repost-post"),
    
    
    
    
    path("post/<slug:slug>/comments/<uuid:comment_id>/replies/", CommentRepliesView.as_view(),name="view-replies"),
    path("post/<slug:slug>/comments/<uuid:comment_id>/reply/", CommentReplyView.as_view()),
    path("comments/<uuid:comment_id>/vote/", CommentVoteView.as_view()), 
    
    #SearchUsersView
    path("search/users/",SearchUsersView.as_view(),name="SearchUsersView"),
    
    #sitemap fetch
    path("posts/sitemap/", PostSitemapView.as_view(), name="post-sitemap"),
    path("profiles/sitemap/", ProfileSitemapView.as_view(), name="profile-sitemap"),

    
    path("views/--views/<slug:slug>/", PostViewsView.as_view(), name="views"),

    path("get/--views/<slug:slug>/", ViewsCount.as_view(), name="get_views_count"),


]