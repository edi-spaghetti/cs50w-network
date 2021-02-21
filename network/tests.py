import datetime
import pytz

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from .models import User, Post


class ModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('test', password='test')
        self.user.save()
        self.user2 = User.objects.create_user('test2', password='test2')
        self.user2.save()
        self.post = Post.objects.create(user=self.user, content='Test Post')
        self.post.save()


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
        expected_keys = {
                'is_staff', 'is_active', 'leader_count', 'is_superuser',
                'last_name', 'id', 'last_login', 'first_name',
                'follower_count', 'email', 'password', 'date_joined',
                'can_follow', 'is_following', 'is_self', 'username'
        }

        for key in serialized.keys():
            self.assertTrue(key in expected_keys)

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

    def test_auto_id_single_linked_field(self):
        """Tests api call that doesn't specify subfield defaults to id"""

        request = ['user']
        result = self.post.serialize(request)
        exp_result = {'user': {'id': 1}}

        self.assertEqual(result, exp_result)

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

    def test_unsorted_multi_linked_field(self):
        self.post2 = Post.objects.create(user=self.user, content='Test Post 2')

        # default linked field sort order is by id
        request = ['id', {'posts': ['id']}]
        exp_result = {'id': 1, 'posts': [{'id': 1}, {'id': 2}]}
        self.assertEqual(self.user.serialize(request), exp_result)

    def test_sorted_multi_linked_field(self):
        self.post2 = Post.objects.create(user=self.user, content='Test Post 2')
        self.post.save()
        self.post2.save()

        # post #2 was created later, so reverse chronological should put
        # it at the start of the list
        request = ['id', {'posts': {'fields': ['id'], 'order': '-timestamp'}}]
        exp_result = {'id': 1, 'posts': [{'id': 2}, {'id': 1}]}
        self.assertEqual(self.user.serialize(request), exp_result)

    def test_sort_multi_link_by_invalid_object(self):
        request = ['id', {'posts': None}]

        with self.assertRaises(ValueError) as e:
            _ = self.user.serialize(request)

        # check we get a useful error message
        self.assertEqual(
            str(e.exception),
            f'multi-link field expects fields as list, '
            f'options as dict, or {self.user.SELECT_ALL}'
            f' - got {type(None)}'
        )

    def test_sort_single_linked_field_fails(self):
        request = ['id', {'user': {'fields': ['id'], 'order': '-date_joined'}}]

        with self.assertRaises(ValueError) as e:
            _ = self.post.serialize(request)

        # check we get a useful error message
        self.assertEqual(
            str(e.exception),
            f'valid types are list[str, dict] or {Post.SELECT_ALL} '
            f'- got {type(dict())}'
        )

    def test_select_all_multi_linked(self):

        # ensure user2 has one follower with one post
        self.user.followers.add(self.user2)
        self.user.save()
        self.user2.save()

        # save the timestamp to a known value
        self.post.timestamp = datetime.datetime(
            2021, 2, 1, 21, 21, 21, tzinfo=pytz.UTC
        )
        self.post.save()

        request = [{'leaders': [{'posts': True}]}]
        response = self.user2.serialize(request)
        exp_result = {
            'leaders': [{
                'posts': [{
                    'timestamp': 'Mon Feb  1 21:21:21 2021',
                    'content': 'Test Post',
                    'id': 1,
                    'like_count': 0,
                    'username': 'test',
                    'user': {
                        'id': 1
                    }
                }]
            }]
        }

        self.assertEqual(response, exp_result)

    def test_user_can_follow_other(self):
        self.user.set_context(self.user2)
        self.assertTrue(self.user.can_follow)

    def test_user_cannot_follow_self(self):
        self.user.set_context(self.user)
        self.assertFalse(self.user.can_follow)

    def test_anon_cannot_follow(self):
        self.user.set_context(AnonymousUser())
        self.assertFalse(self.user.can_follow)

    def test_user_is_following(self):

        # user starts with no followers
        self.assertFalse(self.user.followers.all().exists())

        # add one, and set follower as context
        self.user.followers.add(self.user2)
        self.user.set_context(self.user2)

        # user now has followers, and with follower as context
        # we can query api to confirm
        self.assertTrue(self.user.followers.all().exists())
        self.assertTrue(self.user.is_following)

    def test_update_direct_value(self):

        self.assertNotEqual(self.user.first_name, 'Test')

        request = {'model': 'user', 'id': 1, 'first_name': 'Test'}
        result = self.user.update(request, self.user)

        self.assertEqual(
            result,
            {'model': 'user', 'id': 1, 'first_name': 'Test'}
        )
        self.assertEqual(self.user.first_name, 'Test')

    def test_update_set_multi_linked(self):

        request = {'model': 'user', 'id': 1, 'followers': 2}
        result = self.user.update(request, self.user2, {'followers': 'set'})

        self.assertEqual(
            result,
            {'model': 'user', 'id': 1, 'followers': [{'id': 2}]}
        )
        self.assertTrue(self.user2 in self.user.followers.all())

    def test_update_add_multi_linked(self):
        self.user3 = User.objects.create_user('test3', password='test3')
        self.user3.save()
        self.user.followers.add(self.user3)
        self.user.save()

        request = {'model': 'user', 'id': 1, 'followers': 2}
        result = self.user.update(request, self.user2, {'followers': 'add'})

        self.assertEqual(
            result,
            {'model': 'user', 'id': 1, 'followers': [{'id': 2}, {'id': 3}]}
        )
        self.assertTrue(self.user2 in self.user.followers.all())
        self.assertTrue(self.user3 in self.user.followers.all())

    def test_update_remove_multi_linked(self):
        self.user3 = User.objects.create_user('test3', password='test3')
        self.user3.save()
        self.user.followers.add(self.user3)
        self.user.followers.add(self.user2)
        self.user.save()

        request = {'model': 'user', 'id': 1, 'followers': 2}
        result = self.user.update(request, self.user2, {'followers': 'remove'})

        self.assertEqual(
            result,
            {'model': 'user', 'id': 1, 'followers': [{'id': 3}]}
        )
        self.assertTrue(self.user2 not in self.user.followers.all())
        self.assertTrue(self.user3 in self.user.followers.all())

    def test_parse_equal_filter(self):

        filter_ = [{'id': {'is': 1}}]
        includes, excludes = self.user.parse_filters(filter_)

        self.assertEqual(includes, {'id__exact': 1})
        self.assertEqual(excludes, {})

    def test_convert_number_filter_value(self):

        filter_ = [{'id': {'is': '1'}}]
        includes, excludes = self.user.parse_filters(filter_)

        self.assertEqual(includes, {'id__exact': 1})
        self.assertEqual(excludes, {})

    def test_parse_not_equal_filter(self):

        filter_ = [{'id': {'not': 1}}]
        includes, excludes = self.user.parse_filters(filter_)

        self.assertEqual(includes, {})
        self.assertEqual(excludes, {'id__exact': 1})

    def test_parse_in_filter(self):

        filter_ = [{'id': {'in': [1, 2, 3]}}]
        includes, excludes = self.user.parse_filters(filter_)

        self.assertEqual(includes, {'id__in': [1, 2, 3]})
        self.assertEqual(excludes, {})

    def test_convert_number_in_filter_value(self):

        filter_ = [{'id': {'in': ['1', '2', '3']}}]
        includes, excludes = self.user.parse_filters(filter_)

        self.assertEqual(includes, {'id__in': [1, 2, 3]})
        self.assertEqual(excludes, {})


class PostTests(ModelTests):

    def test_user_can_like_post(self):

        self.assertTrue(
            self.post.has_edit_permissions(
                'likes', self.user2.id, self.user2
            )
        )

    def test_user_cannot_edit_others_likes(self):

        with self.assertRaises(PermissionError) as p:
            self.post.has_edit_permissions(
                'likes', self.user2.id, self.user
            )

        # assert we get a useful error message
        self.assertEqual(
            p.exception.args,
            ("user '1' may not edit field 'likes' with value '2' "
             "on post '1' owned by user '1'", )
        )
