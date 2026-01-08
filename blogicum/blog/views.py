from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from .models import Post, Category, Comment
from .forms import PostForm, CommentForm, RegistrationForm

User = get_user_model()


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


def get_visible_posts():
    """Базовый набор постов для Главной и Категорий: только публичные."""
    return Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')

def index(request):
    """Главная страница: всегда только публичные посты."""
    post_list = get_visible_posts() # Убрали request.user
    paginator = Paginator(post_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'blog/index.html', {'page_obj': page_obj})

def category_posts(request, category_slug):
    """Категория: только публичные посты этой категории."""
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    post_list = get_visible_posts().filter(category=category)
    paginator = Paginator(post_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'blog/category.html', {'category': category, 'page_obj': page_obj})


def post_detail(request, id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'category', 'location')
        .annotate(comment_count=Count('comments')),
        id=id
    )

    can_view = True
    if not post.is_published:
        can_view = request.user.is_authenticated and request.user == post.author
    
    
    if post.pub_date > timezone.now():
        can_view = request.user.is_authenticated and request.user == post.author
    
    
    if not post.category.is_published:
        can_view = request.user.is_authenticated and request.user == post.author
    
    if not can_view:
        return render(request, 'pages/404.html', status=404)
    
    
    comments = post.comments.all().order_by('created_at')
    
    
    form = CommentForm() if request.user.is_authenticated else None
    
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    
    return render(request, 'blog/post_detail.html', context)


def profile(request, username):
    """Страница профиля пользователя"""
    profile_user = get_object_or_404(User, username=username)
    
    if request.user == profile_user:
        user_posts = Post.objects.filter(
            author=profile_user
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    else:
        user_posts = Post.objects.filter(
            author=profile_user,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    
    paginator = Paginator(user_posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/profile.html', {
        'profile_user': profile_user,
        'page_obj': page_obj
    })


@login_required
def create_post(request):
    """Создание нового поста"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if not post.pub_date:
                post.pub_date = timezone.now()
            
            if post.category and not post.category.is_published:
                form.add_error('category', 'Эта категория не опубликована')
            elif post.location and not post.location.is_published:
                form.add_error('location', 'Эта локация не опубликована')
            else:
                post.save()
                return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()
    
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, id):
    """Редактирование поста"""
    post = get_object_or_404(Post, id=id)
    
    if request.user != post.author:
        return redirect('blog:post_detail', id=post.id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=post.id)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def delete_post(request, id):
    """Удаление поста - используем шаблон create.html для подтверждения"""
    post = get_object_or_404(Post, id=id)
    
    if request.user != post.author:
        return HttpResponseForbidden("Вы не можете удалить этот пост")
    
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    """Добавление нового комментария"""
    post = get_object_or_404(Post, id=post_id)
    
    if not post.is_published or post.pub_date > timezone.now():
        if request.user != post.author:
            return HttpResponseForbidden("Вы не можете комментировать этот пост")
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    
    return redirect('blog:post_detail', id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария"""
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if request.user != comment.author:
        return redirect('blog:post_detail', id=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=post_id)

    form = CommentForm(instance=comment)

    return render(request, 'blog/comment.html', {
        'form': form,    
        'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария"""
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if request.user != comment.author:
        return redirect('blog:post_detail', id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=post_id)

    return render(request, 'blog/comment_delete.html', {
        'comment': comment,
        'post': post,
    })