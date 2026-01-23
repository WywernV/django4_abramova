from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.views.generic import CreateView
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


def annotate_comments_count(queryset):
    return queryset.annotate(comment_count=Count('comments')).order_by('-pub_date')


def get_paginated_page(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_visible_posts(request_user=None, for_profile=False, profile_user=None):
    posts = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        category__is_published=True
    )
    
    if not for_profile:
        return posts.filter(
            is_published=True,
            pub_date__lte=timezone.now()
        )
    else:
        if request_user and request_user.is_authenticated and request_user == profile_user:
            return posts.filter(author=profile_user)
        else:
            return posts.filter(
                author=profile_user,
                is_published=True,
                pub_date__lte=timezone.now()
            )


def index(request):
    post_list = get_visible_posts(request.user)
    post_list_with_comments = annotate_comments_count(post_list)
    page_obj = get_paginated_page(request, post_list_with_comments, 10)
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    
    post_list = get_visible_posts(request.user).filter(category=category)
    post_list_with_comments = annotate_comments_count(post_list)
    page_obj = get_paginated_page(request, post_list_with_comments, 10)
    
    return render(request, 'blog/category.html', {
        'category': category, 
        'page_obj': page_obj
    })


def post_detail(request, post_id):
    post = get_object_or_404(
        annotate_comments_count(
            Post.objects.select_related('author', 'category', 'location')
        ),
        id=post_id
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
    profile_user = get_object_or_404(User, username=username)
    
    if request.user == profile_user:
        user_posts = Post.objects.filter(
            author=profile_user,
            category__is_published=True
        )
    else:
        user_posts = Post.objects.filter(
            author=profile_user,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )
    
    user_posts_with_comments = annotate_comments_count(user_posts)
    page_obj = get_paginated_page(request, user_posts_with_comments, 10)
    
    return render(request, 'blog/profile.html', {
        'profile': profile_user,
        'page_obj': page_obj
    })


@login_required
def create_post(request):
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
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post.id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post.id)
    
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if not post.is_published or post.pub_date > timezone.now():
        if request.user != post.author:
            return redirect('blog:post_detail', post_id=post.id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(instance=comment)

    return render(request, 'blog/comment.html', {
        'form': form,
        'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/comment.html', {
        'comment': comment,
    })