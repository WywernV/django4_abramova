from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from pages.views import RegistrationView, ProfileView, ProfileUpdateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    
    path('auth/', include('django.contrib.auth.urls')),
    path('auth/registration/', RegistrationView.as_view(), name='registration'),
    
    
    path('profile/<str:username>/', ProfileView.as_view(), name='profile'),
    path('profile/<str:username>/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    
    
    path('pages/', include('pages.urls')),
    
    
    path('', include('blog.urls')),
]


handler403 = 'pages.views.csrf_failure'
handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'

