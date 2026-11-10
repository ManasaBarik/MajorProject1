from rest_framework.routers import DefaultRouter
from .views import BusinessViewSet
r=DefaultRouter();r.register("businesses",BusinessViewSet,basename="business");urlpatterns=r.urls
