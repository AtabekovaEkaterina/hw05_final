import shutil
import tempfile

from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.user_2 = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
            image=cls.uploaded
        )
        cls.form = PostForm()
        cls.pages_names_templates = [
            (reverse('posts:index'), 'posts/index.html'),
            (reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}
            ), 'posts/group_list.html'
            ),
            (reverse(
                'posts:profile', kwargs={'username': cls.user}
            ), 'posts/profile.html'
            ),
            (reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            ), 'posts/post_detail.html'
            ),
            (reverse('posts:post_create'), 'posts/create_post.html'),
            (reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}
            ), 'posts/create_post.html'
            ),
        ]
        cls.page_follow = {
            'сreate_follow': reverse(
                'posts:profile_follow', kwargs={
                    'username': PostPagesTests.user
                }
            ),
            'check_follow': reverse('posts:follow_index'),
            'delete_follow': reverse(
                'posts:profile_unfollow', kwargs={
                    'username': PostPagesTests.user
                }
            ),
            'follow_to_yourself': reverse(
                'posts:profile_follow', kwargs={
                    'username': PostPagesTests.user_2
                }
            ),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user_2)
        self.author = Client()
        self.author.force_login(PostPagesTests.user)

    def correct_context_page_obj(self, object_post):
        test_author = self.assertEqual(
            object_post.author, PostPagesTests.user
        )
        test_group = self.assertEqual(
            object_post.group, PostPagesTests.group
        )
        test_text = self.assertEqual(
            object_post.text, PostPagesTests.post.text
        )
        test_image = self.assertEqual(
            object_post.image, PostPagesTests.post.image
        )
        return test_author, test_group, test_text, test_image

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        for pages_names, template in PostPagesTests.pages_names_templates:
            with self.subTest(pages_names=pages_names):
                response = self.author.get(pages_names)
                self.assertTemplateUsed(response, template)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        cache.clear()
        page_name = reverse('posts:index')
        response = self.authorized_client.get(page_name)
        object_post = response.context['page_obj'][0]
        self.correct_context_page_obj(object_post)

    def test_group_list_pages_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        page_name = reverse(
            'posts:group_list', kwargs={'slug': PostPagesTests.group.slug}
        )
        response = self.authorized_client.get(page_name)
        object_post = response.context['page_obj'][0]
        self.correct_context_page_obj(object_post)
        group_object = response.context['group']
        self.assertEqual(group_object.title, PostPagesTests.group.title)
        self.assertEqual(group_object.slug, PostPagesTests.group.slug)
        self.assertEqual(
            group_object.description, PostPagesTests.group.description
        )

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        page_name = reverse(
            'posts:profile', kwargs={'username': PostPagesTests.user}
        )
        response = self.authorized_client.get(page_name)
        object_post = response.context['page_obj'][0]
        self.correct_context_page_obj(object_post)
        author_object = response.context['author']
        self.assertEqual(author_object.username, PostPagesTests.user.username)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        page_name = reverse(
            'posts:post_detail', kwargs={'post_id': PostPagesTests.post.id}
        )
        response = self.authorized_client.get(page_name)
        object_post = response.context['post']
        self.correct_context_page_obj(object_post)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.author.get(reverse(
            'posts:post_edit', kwargs={'post_id': PostPagesTests.post.id}
        ))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        object_post = response.context['post']
        self.assertEqual(object_post.text, PostPagesTests.post.text)
        self.assertEqual(object_post.group, PostPagesTests.group)
        self.assertEqual(response.context['is_edit'], True)
        self.assertIsInstance(response.context['form'], PostForm)

    def test_cache_works_for_index_pages(self):
        """Кэширование страницы index работает:
        при удалении записей из БД, они остаются в response.content,
        до тех пор, пока кэш не будет очищен.
        """
        page_name = reverse('posts:index')
        first_response = self.authorized_client.get(page_name)
        Post.objects.all().delete
        second_response = self.authorized_client.get(page_name)
        self.assertEqual(first_response.content, second_response.content)
        cache.clear()
        third_response = self.authorized_client.get(page_name)
        self.assertNotEqual(third_response.content, first_response.content)

    def test_profile_follow_page_for_authorized_client(self):
        """Авторизованный пользователь может подписаться на другого."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            PostPagesTests.page_follow['сreate_follow']
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(Follow.objects.last().user, PostPagesTests.user_2)
        self.assertEqual(Follow.objects.last().author, PostPagesTests.user)

    def test_profile_follow_page_request_follow_to_yourself(self):
        """Авторизованный пользователь не может подписаться на себя."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            PostPagesTests.page_follow['follow_to_yourself']
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_profile_unfollow_page_for_authorized_client(self):
        """ Авторизованный пользователь может удалить подписку."""
        self.authorized_client.get(
            PostPagesTests.page_follow['сreate_follow']
        )
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            PostPagesTests.page_follow['delete_follow']
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_profile_follow_page_for_guest_client(self):
        """Неавторизованный пользователь не может подписаться."""
        follow_count = Follow.objects.count()
        self.guest_client.get(
            PostPagesTests.page_follow['сreate_follow']
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_follow_index_pages_for_authorized_client(self):
        """
        После осуществления подписки авторизованным пользователем,
        посты появляются у него на странице подписок.
        """
        first_response = self.authorized_client.get(
            PostPagesTests.page_follow['check_follow']
        )
        self.authorized_client.get(
            PostPagesTests.page_follow['сreate_follow']
        )
        second_response = self.authorized_client.get(
            PostPagesTests.page_follow['check_follow']
        )
        self.assertNotEqual(first_response.content, second_response.content)

    def test_follow_index_pages_for_not_following_client(self):
        """
        Пост не появляется на странице подписок пользователя
        после его создания, если у пользователя нет подписки
        на автора поста.
        """
        first_response = self.authorized_client.get(
            PostPagesTests.page_follow['check_follow']
        )
        Post.objects.create(
            author=PostPagesTests.user,
            group=PostPagesTests.group,
            text='Новый пост',
        )
        second_response = self.authorized_client.get(
            PostPagesTests.page_follow['check_follow']
        )
        self.assertEqual(first_response.content, second_response.content)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.user_2 = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for i in range(settings.POSTS_TO_CHECK_PAGINATOR):
            cls.post = Post.objects.create(
                author=cls.user,
                group=cls.group,
                text=f'Тестовый пост{i}',
            )
        cls.follow = Follow.objects.create(
            user=cls.user_2,
            author=cls.user,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorTests.user_2)

    def test_paginator_index_group_list_profile_follow_index_pages(self):
        """Проверка работы paginator index, group_list, profile, follow_index.
        На первых страницах отражено 10 постов,
        на вторых страницах отражно - 2 поста.
        """
        cache.clear()
        pages_names = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': PaginatorTests.group.slug}
            ),
            reverse(
                'posts:profile', kwargs={'username': PaginatorTests.user}
            ),
            reverse('posts:follow_index'),
        ]
        for page_name in pages_names:
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_PER_PAGE
                )
                response = self.authorized_client.get(page_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_TO_CHECK_PAGINATOR - settings.POSTS_PER_PAGE
                )
