from django.urls import path
from .views import (ConversationListCreateView, ConversationMessagesView,MessageReactionView,MessageReadView,OfferActionView,
                    MessageDeleteView,MessageDeleteForMeView,ConversationDeleteView,GroupCreateView,GroupMembersView,
                    GroupMemberDetailView,GroupLeaveView,
                    GroupSettingsView,UnreadCountView,UserSearchView
                    )

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view()),
    path("conversations/unreadCount/", UnreadCountView.as_view()),
    path("conversations/groups/", GroupCreateView.as_view()),
    path("conversations/groups/<uuid:conversation_id>/", GroupSettingsView.as_view()),
    path("conversations/groups/<uuid:conversation_id>/members/", GroupMembersView.as_view()),
    path("conversations/groups/<uuid:conversation_id>/members/<uuid:target_user_id>/", GroupMemberDetailView.as_view()),
    path("conversations/groups/<uuid:conversation_id>/leave/", GroupLeaveView.as_view()),
    path("conversations/delete/<uuid:conversation_id>/conversation/", ConversationDeleteView.as_view()),
    path("conversations/message/delete-for-me/<uuid:conversation_id>/<uuid:message_id>/", MessageDeleteForMeView.as_view()),
    path("conversations/messages/<uuid:message_id>/read/", MessageReadView.as_view()),
    path("messages/<uuid:message_id>/offer/", OfferActionView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/", ConversationMessagesView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/<uuid:message_id>/", MessageDeleteView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/<uuid:message_id>/reactions/", MessageReactionView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/<uuid:message_id>/reactions/<str:emoji>/", MessageReactionView.as_view()),
    path("users/search/", UserSearchView.as_view()),
]