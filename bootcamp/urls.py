from rest_framework import routers

from .views import CourseViewset, MyCourseViewset, CourseAdvViewSet, CourseAdsViewSet

router = routers.SimpleRouter()
router.register("courses", CourseViewset)
router.register("my-courses", MyCourseViewset)
# TODO deprecated
router.register("courses-adv", CourseAdvViewSet)
router.register("courses-ads", CourseAdsViewSet)


urlpatterns = router.urls
