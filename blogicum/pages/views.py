from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .forms import RegistrationForm


# Обработчики ошибок
def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)


def server_error(request):
    return render(request, 'pages/500.html', status=500)


# Регистрация
class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


# Профиль пользователя
class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from blog.models import Post
        posts = Post.objects.filter(author=self.object)

        # Пагинация - 10 постов на страницу
        paginator = Paginator(posts, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['page_obj'] = page_obj
        return context


# Редактирование профиля
class ProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    template_name = 'blog/profile_edit.html'
    fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_object(self, queryset=None):
        # Получаем пользователя по username
        username = self.kwargs.get('username')
        return get_object_or_404(User, username=username)
    
    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'username': self.object.username})
    
    def test_func(self):
        user = self.get_object()
        return self.request.user == user
