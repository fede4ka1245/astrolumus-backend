from django.urls import include, path

from rest_framework import routers

from .views import CategoryViewSet, get_topic_info, TopicViewSet, CommentViewSet, ImageViewSet, get_forum_rules, TopicMembersViewSet

router = routers.SimpleRouter()
router.register("categories", CategoryViewSet)
router.register("topics", TopicViewSet)
router.register("topics-members", TopicMembersViewSet)
router.register("comments", CommentViewSet)
router.register("images", ImageViewSet)

urlpatterns = [
    path("rules/", get_forum_rules, name="forum_rules"),
    path('public_topic/<int:id>/', get_topic_info, name='get_topic_info'),
]

urlpatterns += router.urls
