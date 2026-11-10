from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet
r=DefaultRouter();r.register("applications",ApplicationViewSet,basename="application");urlpatterns=r.urls
