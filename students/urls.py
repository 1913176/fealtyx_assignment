# students/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('students/', views.student_list),
    path('students/<int:pk>/', views.student_detail),
    path('students/<int:pk>/summary/', views.student_summary),
]