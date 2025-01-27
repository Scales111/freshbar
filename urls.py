from django.urls import path, re_path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.generic import TemplateView



urlpatterns = [
    path('login', views.login.as_view(), name='login'),
    path('profile', views.profile, name='profile'),
    path('register', views.register.as_view(), name='register'),
    path('tasks', views.get_tasks, name='get_tasks'),
    path('submit-answer', views.submit_answer, name='submit_answer'),
    path('user-answers/<str:userId>', views.user_answers_view, name='user-answers'),
    # path('get-user-answer/', views.get_user_answer, name='get-user-answer'),
    path('olympiad', views.olympiad_view.as_view(), name='olympiad'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('check-olympiad', views.check_olympiad, name='check-olympiad'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', views.index, name='index'),  # Маршрут для рендера главной страницы
    re_path(r'^(?!api/).*$', views.index, name='login'),
]
