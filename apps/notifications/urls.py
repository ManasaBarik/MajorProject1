from django.urls import path
from .views import *
urlpatterns=[path("notifications/",ListView.as_view()),path("notifications/<int:pk>/read/",ReadView.as_view()),path("notifications/read-all/",ReadAllView.as_view())]
