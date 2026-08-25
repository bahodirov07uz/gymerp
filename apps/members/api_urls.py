from rest_framework.routers import DefaultRouter

from .api_views import MemberViewSet

router = DefaultRouter()
router.register("members", MemberViewSet, basename="api-member")

urlpatterns = router.urls
