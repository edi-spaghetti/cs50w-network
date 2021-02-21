from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.db import models

from .utils import (
    ModelExtension,
    field_label,
)


class User(ModelExtension, AbstractUser):
    followers = models.ManyToManyField('User', related_name='leaders')

    summary = field_label()
    contextual = field_label()

    def sanitize_context(self, user):
        # make sure we cast request user to at least anonymous user
        not_user = not isinstance(user, AbstractUser)
        not_anon = not isinstance(user, AnonymousUser)
        if not_user and not_anon:
            user = AnonymousUser()

        return user

    def has_read_permissions(self, field, value, context):
        """
        TODO
        :param field:
        :param value:
        :param context:
        :return:
        """
        return True

    def has_edit_permissions(self, field, value, context):
        """
        Authorises edit action on given field
        :param field: Field to apply change
        :param value: Value to apply to field
        :param context: User requesting to make the change
        :return: True if has permissions
        :raises: PermissionError if not allowed
        """

        if isinstance(context, AnonymousUser):
            raise PermissionError(
                f'login required'
            )
        elif isinstance(context, AbstractUser) and not context.is_superuser:
            # logged in users can edit fields on their own user, or add/remove
            # themselves as followers of other users
            editing_self = (
                    self.pk == context.pk or
                    (field == 'followers' and value == context.pk)
            )
            if not editing_self:
                raise PermissionError(
                    f'user may not edit other user fields'
                )
        else:
            raise PermissionError(
                f'invalid context, expected User - got {type(context)}'
            )

        return True

    @property
    @summary
    def follower_count(self):
        return self.followers.count()

    @property
    @summary
    def leader_count(self):
        return self.leaders.count()

    @property
    @contextual
    def can_follow(self):

        if self._context is None:
            self.set_context(self.sanitize_context(None))

        return self._context.is_authenticated and self._context.pk != self.pk

    @property
    @contextual
    def is_following(self):

        if self._context is None:
            self.set_context(self.sanitize_context(None))

        return self.followers.filter(id=self._context.id).exists()

    @property
    @contextual
    def is_self(self):

        if self._context is None:
            self.set_context(self.sanitize_context(None))

        return self.pk == self._context.pk

    @property
    def date_joined__serial(self):
        return self.date_joined.strftime('%c')


class Post(ModelExtension, models.Model):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='posts'
    )
    content = models.CharField(max_length=140)
    timestamp = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField('User', related_name='liked_posts')

    summary = field_label()
    contextual = field_label()

    def sanitize_context(self, user):
        # make sure we cast request user to at least anonymous user
        not_user = not isinstance(user, AbstractUser)
        not_anon = not isinstance(user, AnonymousUser)
        if not_user and not_anon:
            user = AnonymousUser()

        return user

    def has_read_permissions(self, field, value, context):
        """
        TODO
        :param field:
        :param value:
        :param context:
        :return:
        """
        return True

    def has_edit_permissions(self, field, value, context):
        """
        Authorises edit action on given field
        :param field: Field to apply change
        :param value: Value to apply to field
        :param context: User requesting to make the change
        :return: True if has permissions
        :raises: PermissionError if not allowed
        """
        if isinstance(context, AnonymousUser):
            raise PermissionError(
                f'login required'
            )
        elif isinstance(context, AbstractUser) and not context.is_superuser:
            # logged in users can only edit fields on their own posts
            editing_self = (
                (self.user.pk == context.pk and field == 'content') or
                (field == 'likes' and value == context.pk)
            )
            if not editing_self:
                raise PermissionError(
                    f"user '{context.pk}' may not edit field '{field}' "
                    f"with value '{value}' on post '{self.id}' owned by "
                    f"user '{self.user.pk}'"
                )
        else:
            raise PermissionError(
                f'invalid context, expected User - got {type(context)}'
            )

        return True

    @property
    def timestamp__serial(self):
        return self.timestamp.strftime('%c')

    @property
    @summary
    def username(self):
        return self.user.username

    @property
    @summary
    def like_count(self):
        return self.likes.count()

    @property
    @contextual
    def i_like(self):

        if self._context is None:
            self.set_context(self.sanitize_context(None))

        return self.likes.filter(id=self._context.id).exists()

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
