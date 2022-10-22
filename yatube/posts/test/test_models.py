from django.conf import settings
from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_autor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост' * settings.MULTIPLES_POST_TEXT_FOR_TEST_MODEL,
        )

    def test_models_have_correct_object_names(self):
        """У моделей Post и Group корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        field_str = {
            post.text[:settings.LIMIT_CHARACTERS_FOR_POST]: str(post),
            group.title: str(group),
        }
        for field, expected_value in field_str.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_value)
