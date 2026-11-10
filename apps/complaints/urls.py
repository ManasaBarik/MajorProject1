from rest_framework.routers import DefaultRouter
from .views import ComplaintViewSet
r=DefaultRouter();r.register("complaints",ComplaintViewSet,basename="complaint");urlpatterns=r.urls
