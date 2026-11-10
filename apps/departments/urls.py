from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, CategoryDepartmentMappingViewSet

r = DefaultRouter()
r.register("departments", DepartmentViewSet)
r.register("category-mappings", CategoryDepartmentMappingViewSet)
urlpatterns = r.urls
