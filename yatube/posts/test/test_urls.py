from http import HTTPStatus

from django.test import Client, TestCase

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.author = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )
        cls.urls_templates = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{cls.user}/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html'),
            ('/create/', 'posts/create_post.html'),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html'),
            ('/posts/test_error/', 'core/404.html'),
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.author = Client()
        self.author.force_login(PostURLTests.author)

    def test_correct_templates_for_all_urls(self):
        """Все страницы используют корректные шаблоны"""
        for url, template in PostURLTests.urls_templates:
            with self.subTest(url=url):
                response = self.author.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_pages_for_any_user(self):
        """Страницы доступные любому пользователю"""
        for url, _ in self.urls_templates:
            with self.subTest(url=url):
                if url == '/create/':
                    break
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_page_for_authorized_client(self):
        """Страница /create/ доступна только авторизованному пользователю"""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_redirects_page_for_authorized_client(self):
        """Страница /create/ перенаправляет неавторизованного пользователя"""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, ('/auth/login/?next=/create/'))

    def test_urls_page_for_author(self):
        """Страница posts/<post_id>/edit/ доступна только автору."""
        response = self.author.get(f'/posts/{PostURLTests.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.authorized_client.get(
            f'/posts/{PostURLTests.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_redirects_page_for_author(self):
        """Страница posts/<post_id>/edit/ перенаправляет не автора поста."""
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response, (
                f'/auth/login/?next=/posts/{PostURLTests.post.id}/edit/'
            )
        )
        response = self.authorized_client.get(
            f'/posts/{PostURLTests.post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response, (f'/posts/{PostURLTests.post.id}/'))

    def test_page_does_not_exist(self):
        """Запрос к несуществующей странице выдает ошибку."""
        response = self.authorized_client.get('/posts/test_error/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.guest_client.get('/posts/test_error/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.author.get('/posts/test_error/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
