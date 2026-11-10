from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet
r=DefaultRouter();r.register("services",ServiceViewSet);urlpatterns=r.urls
