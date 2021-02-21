import os
import django
import random
import datetime
import pytz

# set seed so demo can be reproduced
random.seed(1)

settings_module = 'project4.settings'
os.environ['DJANGO_SETTINGS_MODULE'] = settings_module

django.setup()
from network.models import *
from lorem import LOREM

# drop existing database (if any) and run latest migration
os.system(f'python {os.path.dirname(__file__)}/../manage.py flush')
os.system(f'python {os.path.dirname(__file__)}/../manage.py makemigrations')
os.system(f'python {os.path.dirname(__file__)}/../manage.py migrate')

print('Creating users')
for i in range(random.randint(5, 10)):
    user = User.objects.create_user(f'user{i}', password=f'user{i}')
    user.save()

print('Creating followers')
for user in User.objects.all():
    followers = User.objects.exclude(pk=user.id)
    followers = list(followers.values_list('id', flat=True))
    random.shuffle(followers)
    user.followers.set(followers[0:random.randint(0, len(followers))])
    user.save()

print('Creating posts')
for user in User.objects.all():
    for i in range(random.randint(0, 10)):

        # build up post content from random words up to 140 characters
        text = list()
        for i in range(random.randint(5, 30)):
            text.append(random.choice(LOREM))
            # +1 to account for spaces, -1 for last word no space
            length = sum([len(w) + 1 for w in text]) - 1
            if length > 140:
                text.pop(-1)
        text = ' '.join(text)

        # create a random post time
        offset = datetime.timedelta(seconds=random.randint(1, 10000000))
        print(f'User {user} post {i} -> {offset}')

        post = Post(user=user, content=text)
        post.save()
        post.timestamp = post.timestamp - offset
        post.save()

print('Creating likes')
for post in Post.objects.all():
    fans = post.user.followers.all().values_list('id', flat=True)
    f = len(fans)
    lb = int(f * 0.5)
    ub = int(f * 0.9)
    fans = fans[:(random.randint(lb, ub))]
    new_fans = User.objects.exclude(id__in=fans)[:random.randint(0, 5)]
    new_fans = new_fans.values_list('id', flat=True)
    fans.extend(new_fans)
    post.likes.set(fans)
    post.save()
