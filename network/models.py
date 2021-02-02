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
