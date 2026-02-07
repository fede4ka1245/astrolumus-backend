from rest_framework import routers

from .views import BannerViewSet, BannerViewSetV2

router = routers.SimpleRouter()
router.register("banners", BannerViewSet)
router.register("banners_v2", BannerViewSetV2)


urlpatterns = router.urls
