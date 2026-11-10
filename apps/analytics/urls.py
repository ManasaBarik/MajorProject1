from django.urls import path
from .views import OverviewView,CategoriesView,DepartmentsView,WardsView,TrendsView,MapComplaintsView,MapHeatmapView
urlpatterns=[
 path("analytics/overview/",OverviewView.as_view()),
 path("analytics/complaints/categories/",CategoriesView.as_view()),
 path("analytics/complaints/departments/",DepartmentsView.as_view()),
 path("analytics/complaints/wards/",WardsView.as_view()),
 path("analytics/complaints/trends/",TrendsView.as_view()),
 path("analytics/map/complaints/",MapComplaintsView.as_view()),
 path("analytics/map/heatmap/",MapHeatmapView.as_view()),
]
