from django.test import TestCase
from .models import User, Post, Like


class ModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('test', password='test')
        self.user2 = User.objects.create_user('test2', password='test2')
        self.post = Post.objects.create(user=self.user, content='Test Post')
        self.like = Like.objects.create(user=self.user2, post=self.post)


class UserTests(ModelTests):

    def test_serialize_direct_field(self):
        self.assertEqual(self.user.serialize(['id']), {'id': 1})

    def test_serialize_linked_field(self):
        self.assertEqual(
            self.user.serialize([{'posts': ['id']}]),
            {'posts': [{'id': 1}]}
        )

    def test_serialize_all_direct(self):
        serialized = self.user.serialize(True)
        expected_keys = [
                'is_staff', 'is_active', 'leader_count', 'is_superuser',
                'last_name', 'id', 'last_login', 'first_name',
                'follower_count', 'email', 'password', 'date_joined',
                'can_follow', 'is_following', 'username'
        ]

        for key in expected_keys:
            self.assertTrue(key in serialized)

    def test_serialize_invalid_direct_field(self):
        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize(['invalid'])

        # check we get a useful error message
        self.assertEqual(
            str(e.exception),
            f'invalid is not a direct field of {User}'
        )

    def test_serialize_invalid_linked_field(self):
        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize([{'invalid': []}])

        # check we got a useful error message
        self.assertEqual(
            str(e.exception),
            f'invalid is not a linked field of {User}'
        )

    def test_serialize_direct_as_linked_field(self):
        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize([{'username': []}])

        # check we got a useful error message
        self.assertEqual(
            str(e.exception),
            f'username is not a linked field of {User}'
        )

    def test_serialize_invalid_type_outer(self):
        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize({'invalid'})

        self.assertEqual(
            str(e.exception),
            f'valid types are list[str, dict] or {User.SELECT_ALL} '
            f'- got {type(set())}'
        )

    def test_serialize_invalid_type_inner(self):
        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize([{'invalid'}])

        # check we got a useful error message
        self.assertEqual(
            str(e.exception),
            f'expected inner items str or dict - got {type(set())}'
        )
