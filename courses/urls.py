from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/new/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('chapters/<int:pk>/review/', views.chapter_review, name='chapter_review'),
    path('chapters/<int:pk>/quiz/', views.chapter_quiz, name='chapter_quiz'),
]