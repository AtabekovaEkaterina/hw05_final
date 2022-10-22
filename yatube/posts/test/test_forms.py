import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_edit = Group.objects.create(
            title='Вторая тестовая группа',
            slug='edit-slug',
            description='Группа для измененного поста',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Исходный текст',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.author = Client()
        self.author.force_login(PostFormTests.user)

    def test_form_post_creating(self):
        """
        При отправки валидной формы со страницы post_create
        создается новая запись.
        """
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'author': PostFormTests.user,
            'group': PostFormTests.group.id,
            'text': 'Новый текст',
            'image': uploaded,
        }
        response = self.author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': PostFormTests.user}
            ))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(Post.objects.first().author, PostFormTests.user)
        self.assertEqual(Post.objects.first().group, PostFormTests.group)
        self.assertEqual(Post.objects.first().text, 'Новый текст')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_form_post_editing(self):
        """
        При отправки валидной формы со страницы post_edit
        изменяется старая запись.
        """
        post_count = Post.objects.count()
        form_data = {
            'author': PostFormTests.user,
            'group': PostFormTests.group_edit.id,
            'text': 'Измененный текст',
        }
        response = self.author.post(
            reverse(
                'posts:post_edit', kwargs={'post_id': PostFormTests.user.id}
            ),
            data=form_data,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': PostFormTests.user.id}
            ))
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(
            Post.objects.get(id=PostFormTests.post.id), Post.objects.get(
                author=PostFormTests.user,
                group=PostFormTests.group_edit.id,
                text='Измененный текст'
            ))

    def test_form_post_creating_by_guest_client(self):
        """
        При отправки формы неавторизованным пользователем
        со страницы post_create, запись не создается.
        """
        post_count = Post.objects.count()
        form_data = {
            'group': PostFormTests.group.id,
            'text': 'Новый текст',
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertRedirects(
            response, ('/auth/login/?next=/create/')
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_form_post_editing_by_guest_client(self):
        """
        При отправки формы неавторизованным пользователем
        со страницы post_edit, старая запись не меняется.
        """
        post_count = Post.objects.count()
        form_data = {
            'author': PostFormTests.user,
            'group': PostFormTests.group_edit.id,
            'text': 'Измененный текст',
        }
        response = self.guest_client.post(
            reverse(
                'posts:post_edit', kwargs={'post_id': PostFormTests.user.id}
            ),
            data=form_data,
        )
        self.assertRedirects(
            response, (
                f'/auth/login/?next=/posts/{PostFormTests.post.id}/edit/'
            )
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(
            Post.objects.get(id=PostFormTests.post.id), Post.objects.get(
                author=PostFormTests.user,
                group=PostFormTests.group.id,
                text='Исходный текст'
            ))

    def test_form_add_comment(self):
        """
        При отправки валидной формы со страницы add_comment,
        создается новый комментарий.
        """
        comment_count = Comment.objects.count()
        form_data = {
            'post': PostFormTests.post,
            'author': PostFormTests.user,
            'text': 'Новый комментарий',
        }
        response = self.author.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': PostFormTests.post.id}
            ),
            data=form_data,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': PostFormTests.post.id}
            ))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(Comment.objects.last().post, PostFormTests.post)
        self.assertEqual(Comment.objects.last().author, PostFormTests.user)
        self.assertEqual(Comment.objects.last().text, 'Новый комментарий')

    def test_form_add_comment_by_guest_client(self):
        """
        При отправки формы неавторизованным пользователем
        со страницы add_comment, комментарий не создается.
        """
        comment_count = Comment.objects.count()
        form_data = {
            'post': PostFormTests.post,
            'author': PostFormTests.user,
            'text': 'Новый комментарий',
        }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': PostFormTests.post.id}
            ),
            data=form_data,
        )
        self.assertRedirects(
            response, (
                f'/auth/login/?next=/posts/{PostFormTests.post.id}/comment/'
            )
        )
        self.assertEqual(Comment.objects.count(), comment_count)
