from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from pages.views import RegistrationView, ProfileView, ProfileUpdateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Аутентификация
    path('auth/', include('django.contrib.auth.urls')),
    path('auth/registration/', RegistrationView.as_view(), name='registration'),
    
    # Профили
    path('profile/<str:username>/', ProfileView.as_view(), name='profile'),
    path('profile/<str:username>/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    
    # Статические страницы
    path('pages/', include('pages.urls')),
    
    # Блог (все пути блога теперь в blog/urls.py)
    path('', include('blog.urls')),
]

# Обработчики ошибок
handler403 = 'pages.views.csrf_failure'
handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'

