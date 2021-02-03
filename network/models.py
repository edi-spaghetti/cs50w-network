from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Post(models.Model):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='posts'
    )
    content = models.CharField(max_length=140)
    timestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            'id': self.pk,
            'user': self.user.username,
            'content': self.content,
            'timestamp': self.timestamp.strftime('%c'),
        }

    @classmethod
    def create_from_post(cls, user=None, content=None, **kwargs):
        """
        Creates a :class:`Post` instance from data provided in a POST request
        :param user: Id of the User to link to the created model
        :param content: Text content to add to the created model
        :param kwargs: Additional arguments, included to assure backwards
                       compatibility
        :return: new, unsaved instance of the current class
        """

        try:
            user = int(user)
            user = User.objects.get(pk=user)
        except (ValueError, TypeError):
            # TODO: logging
            print(f'Cannot convert user to int - got {user}')
            return
        except User.DoesNotExist:
            print(f'No User found with id: {user}')
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

    def serialize(self):
        return {
            'id': self.pk,
            'user': self.user.username,
            'post': self.post.pk,
            'timestamp': self.timestamp.strftime('%c'),
        }

    @classmethod
    def create_from_post(cls, user=None, post=None, **kwargs):
        """
        Creates a :class:`Like` instance from data provided in a POST request
        :param user: Id of the user linked to the created like
        :param post: Id of the post linked to created like
        :param kwargs: Additional args for backwards compatibility
        :return: A new, unsaved :class:`Like` instance
        """

        # TODO: create method to get instance from key
        try:
            user = int(user)
            user = User.objects.get(pk=user)
        except (ValueError, TypeError):
            # TODO: logging
            print(f'Cannot convert user to int - got {user}')
            return
        except User.DoesNotExist:
            print(f'No User found with id: {user}')
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
