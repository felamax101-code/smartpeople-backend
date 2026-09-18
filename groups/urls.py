from django.urls import path
from .views import (ProfileApprovalView,PostCreateView,PostListCreateView,CommentCreateView,
                    PostUpvoteView,CommmentReportView,
                    SavedPostView,CatagoryListView,
                    CommentRepliesView,CommentReplyView,CommentVoteView,PostByIdView,
                    PostReportView,UserCommunitiesView,UserCommunitySuggestionaView,
                    CreateGroupView,JoinCommunityView,UserInfoOnCommunity,InviteMemberView,ApproveJoinRequestsView,
                    RemoveMemberView,GetGroupMembersView,ViewJoinRequests,ViewPendingInvites,SearchMembersView,GetAdimnModerator,
                    CommunityInfoView,CommunityRules,MyInvitesView,MySentRequestsView,AcceptInviteView,SearchUsersForRoleAssignment,
                    MakeUserAdminOrModerator,GetAsignedRoles,AsignRoleToAModerator,PendingPostListCreateView,RejecetedPostListCreateView,
                    RejectPostView,ApprovePostView,RequestToJoinAprivateCommunity,AddRemoveCategory,PostViewsView,ViewsCount)


urlpatterns = [
    #admin actions
    path("admin/posts/",ProfileApprovalView.as_view(),name="admin-post-list"),
    path("admin/posts/<uuid:id>",ProfileApprovalView.as_view(),name="admin-post-action"),
    #categories
    path("categories/<slug:slug>/",CatagoryListView.as_view(),name="categories"),
    path("<slug:slug>/posts/",PostCreateView.as_view(),name="create/delete-post"),
    path("posts/edit/<str:slug>/",PostCreateView.as_view(),name="edit-post"),

    path("postbyid/<uuid:id>/",PostByIdView.as_view(),name="get-create/edit/delete-post"),

    path("post/<slug:slug>/",PostCreateView.as_view(),name="get-create/edit/delete-post"),
    path("<slug:slug>/feed/",PostListCreateView.as_view(),name="feed"),
    
    
    #pendingposts
    path("pending/<slug:slug>/feed/",PendingPostListCreateView.as_view(),name="feed"),
    #rejected
    path("rejected/<slug:slug>/feed/",RejecetedPostListCreateView.as_view(),name="feed"),

    #approve post by admin
    path("approvepost/<slug:slug>/",ApprovePostView.as_view(),name="approvepost"),
    ##comments
    #reject post
    path("rejectpost/<slug:slug>/",RejectPostView.as_view(),name="approvepost"),

    path("post/<slug:slug>/comments/",CommentCreateView.as_view(),name="create-comment"),
    path("comment/<uuid:id>/",CommentCreateView.as_view(),name=",delete,edit-comment"),
    path("comment/report/<uuid:id>/",CommmentReportView.as_view(),name="report-comment"),
    
    #gat/saved/unsave posts
    path("wishlist/",SavedPostView.as_view(),name="get/delete-saved-post"),
    path("wishlist/<slug:slug>/",SavedPostView.as_view(),name="saved/unsave-post"),
    
    #post report
    path("post/<uuid:id>/report/",PostReportView.as_view(),name="report-post"),

    
    ##upvote post
    path("post/<str:slug>/upvote/",PostUpvoteView.as_view(),name="like-post"),
    
        
    
    
    path("post/<slug:slug>/comments/<uuid:comment_id>/replies/", CommentRepliesView.as_view(),name="view-replies"),
    path("post/<slug:slug>/comments/<uuid:comment_id>/reply/", CommentReplyView.as_view()),
    path("comments/<uuid:comment_id>/vote/", CommentVoteView.as_view()), 
    
    
    path("mine/",UserCommunitiesView.as_view(),name="my-groups"),
    path("suggestions/",UserCommunitySuggestionaView.as_view(),name="suggestion-groups"),

    path("create/community/",CreateGroupView.as_view(),name="create-community"),
    path("update/community/",CreateGroupView.as_view(),name="update/delete/community"),
    
    path("join/community/",JoinCommunityView.as_view(),name="join-community"),
    
    path("get/user/community/<slug:slug>/",UserInfoOnCommunity.as_view(),name="user-community-info"),
    
    path("invite/<slug:slug>/",InviteMemberView.as_view(),name="invite-user-to-group"),
    path("cancel/invite/<slug:slug>/<uuid:invite_id>/",InviteMemberView.as_view(),name="cancel-user-to-group"),
    
    path("approve/<slug:slug>/request/<uuid:request_id>/",ApproveJoinRequestsView.as_view(),name="approve-join-requests"),
    path("reject/<slug:slug>/request/<uuid:request_id>/",ApproveJoinRequestsView.as_view(),name="reject-delete-join-requests"),
    
    
    path("remove-member/<slug:slug>/<uuid:user_id>/",RemoveMemberView.as_view(),name="remove-member"),
    
    path("members/<slug:slug>/",GetGroupMembersView.as_view(),name="get-group-members"),
    
    path("pending/requests/<slug:slug>/",ViewJoinRequests.as_view(),name="view-join requests"),
    
    path("fetch/pending/invites/<slug:slug>/",ViewPendingInvites.as_view(),name="view-pending-invites"),
    
    path("searchusers/<slug:slug>/",SearchMembersView.as_view(),name="saerch-users"),
    
    path("moderators/admin/<slug:slug>/",GetAdimnModerator.as_view(),name="community-info"),
    
    path("myinvites/",MyInvitesView.as_view(),name="My-invites"),
    path("acceptinvite/<uuid:id>/",AcceptInviteView.as_view(),name="reject-my-invite"),
    path("rejectinvite/<uuid:id>/",AcceptInviteView.as_view(),name="reject-my-invite"),
    
    path("mysentrequests/",MySentRequestsView.as_view(),name="My-invites"),
    path("cancellrequest/<uuid:id>/",RequestToJoinAprivateCommunity.as_view(),name="cancell-my-sent-requests"),
    path("info/<slug:slug>/",CommunityInfoView.as_view(),name="com-info"),
    path("rules/<slug:slug>/",CommunityRules.as_view(),name="com-info"),
    #request made to private community
    path("request-to-join/<slug:slug>/",RequestToJoinAprivateCommunity.as_view(),name=("RequestToJoinAprivateCommunity")),
    #edit group
    path("edit/group/<slug:slug>/",CreateGroupView.as_view(),name="edit-group-details"),
    
    
    path("searchUser-to-asign-community-roles/<slug:slug>/",SearchUsersForRoleAssignment.as_view(),name="searchUsersForRoleAssignment"),
    path("make-a-user-admin-or-moderator/<slug:slug>/",MakeUserAdminOrModerator.as_view(),name="asign-community-role"),
    path("user/get/my-asigned-roles/<slug:slug>/",GetAsignedRoles.as_view(),name="GetAsignedRoles"),
    path("asign-roles-to-a-modeartor/<slug:slug>/",AsignRoleToAModerator.as_view(),name="AsignRoleToAModerator"),
    
    #addremove com category
    path("category/add/<slug:slug>/",AddRemoveCategory.as_view(),name="add-gategory"),
    path("category/remove/<slug:slug>/<uuid:id>",AddRemoveCategory.as_view(),name="rempove-category"),

       path("views/--views/<slug:slug>/", PostViewsView.as_view(), name="views"),

    path("get/--views/<slug:slug>/", ViewsCount.as_view(), name="get_views_count"),

    
]
