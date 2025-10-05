import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Matchify.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from Matchifyapp.models import Post, Comment
User = get_user_model()

username = 'reacttester'
password = 'testpass123'
user, created = User.objects.get_or_create(username=username, defaults={'email':'react@test','is_active':True})
if created:
    user.set_password(password)
    user.save()

c = Client()
logged = c.login(username=username, password=password)
print('logged in', logged)

# create a post
post = Post.objects.create(author=user, content='Test post for comment reactions')
print('post id', post.id)
# create a comment
comment = Comment.objects.create(post=post, author=user, content='Test comment')
print('comment id', comment.id)

# Post a like reaction to comment via AJAX header
resp = c.post(f'/discussion/react/{post.id}/', {'comment_id': comment.id, 'value': '1'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('status', resp.status_code)
print('content-type', resp['Content-Type'] if 'Content-Type' in resp else '')
print('body:', resp.content.decode('utf-8'))

# Check counts in DB
print('DB likes', comment.reactions.filter(value=1).count())
print('DB dislikes', comment.reactions.filter(value=-1).count())
