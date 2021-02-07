from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.db import models


def sanitize_user(user):
    # make sure we cast request user to at least anonymous user
    not_user = not isinstance(user, User)
    not_anon = not isinstance(user, AnonymousUser)
    if user is None or not_user or not_anon:
        user = AnonymousUser()

    return user


def collate_values(fields, callbacks):
    # add valid fields to dict
    serial_dict = dict()

    if fields == '*':
        fields = callbacks.keys()

    for field in fields:
        if field in callbacks:
            value = callbacks[field]()
        else:
            value = None

        serial_dict[field] = value

    return serial_dict


class User(AbstractUser):
    followers = models.ManyToManyField('User', related_name='leaders')

    def serialize(self, fields, request_user=None):

        user = sanitize_user(request_user)

        # callback dict to retrieve values
        callbacks = dict(
            id=lambda: self.pk,
            username=lambda: self.username,
            posts=lambda: [p.serialize() for p in self.posts],
            follower_count=lambda: self.followers.count(),
            leader_count=lambda: self.leaders.count(),
            can_follow=lambda: (
                user.is_authenticated and user.pk != self.pk
            ),
            is_following=lambda: self.followers.filter(id=user.id).exists()
        )

        return collate_values(fields, callbacks)


class Post(models.Model):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='posts'
    )
    content = models.CharField(max_length=140)
    timestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self, fields, request_user=None):

        callbacks = dict(
            id=lambda: self.pk,
            user=lambda: self.user.username,
            content=lambda: self.content,
            timestamp=lambda: self.timestamp.strftime('%c'),
            like_count=lambda: self.likes.count(),
        )

        return collate_values(fields, callbacks)

    @classmethod
    def create_from_post(cls, user=None, content=None, **kwargs):
        """
        Creates a :class:`Post` instance from data provided in a POST request
        :param user: User instance to link to the created model
        :param content: Text content to add to the created model
        :param kwargs: Additional arguments, included to assure backwards
                       compatibility
        :return: new, unsaved instance of the current class
        """

        if user is None:
            print(f'Must provide user')
            return

        return cls(user=user, content=content)


class Like(models.Model):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='likes'
    )
    post = models.ForeignKey(
        'Post', on_delete=models.CASCADE, related_name='likes'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self, fields, request_user=None):

        callbacks = dict(
            id=lambda: self.pk,
            user=lambda: self.user.username,
            post=lambda: self.post.pk,
            timestamp=lambda: self.timestamp.strftime('%c'),
        )

        return collate_values(fields, callbacks)

    @classmethod
    def create_from_post(cls, user=None, post=None, **kwargs):
        """
        Creates a :class:`Like` instance from data provided in a POST request
        :param user: user instance to link to the created like
        :param post: Id of the post linked to created like
        :param kwargs: Additional args for backwards compatibility
        :return: A new, unsaved :class:`Like` instance
        """

        if user is None:
            print(f'Must provide user')
            return

        try:
            post = int(post)
            post = Post.objects.get(pk=post)
        except (ValueError, TypeError):
            # TODO: logging
            print(f'Cannot convert post to int - got {post}')
            return
        except Post.DoesNotExist:
            print(f'No Post found with id: {post}')
            return

        return cls(user=user, post=post)
