from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from .models import Post


class DiscussionSortTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='tester', email='t@test.com', password='pass')
		# Create three posts with staggered created_at timestamps
		now = timezone.now()
		self.p1 = Post.objects.create(author=self.user, content='first')
		self.p2 = Post.objects.create(author=self.user, content='second')
		self.p3 = Post.objects.create(author=self.user, content='third')
		# set timestamps: p1 = now - 3 days, p2 = now - 2 days, p3 = now - 1 day
		Post.objects.filter(pk=self.p1.pk).update(created_at=now - timedelta(days=3))
		Post.objects.filter(pk=self.p2.pk).update(created_at=now - timedelta(days=2))
		Post.objects.filter(pk=self.p3.pk).update(created_at=now - timedelta(days=1))

	def test_sort_oldest(self):
		"""Oldest to Newest should return least recent first (top) and most recent last."""
		self.client.force_login(self.user)
		url = reverse('discussion') + '?sort=oldest'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		posts = resp.context['posts']
		# posts is list of dicts with 'post' key
		ordered = [p['post'].pk for p in posts]
		# Expect p1, p2, p3 (oldest to newest)
		self.assertEqual(ordered, [self.p1.pk, self.p2.pk, self.p3.pk])

	def test_sort_newest(self):
		"""Newest to Oldest should return most recent first."""
		self.client.force_login(self.user)
		url = reverse('discussion') + '?sort=newest'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		posts = resp.context['posts']
		ordered = [p['post'].pk for p in posts]
		# Expect p3, p2, p1 (newest to oldest)
		self.assertEqual(ordered, [self.p3.pk, self.p2.pk, self.p1.pk])

	def test_sort_most_liked(self):
		"""Most liked should order posts by descending like count."""
		User = get_user_model()
		# create two additional users to like posts
		u2 = User.objects.create_user(username='u2', email='u2@test.com', password='pass')
		u3 = User.objects.create_user(username='u3', email='u3@test.com', password='pass')
		# p1: two likes (u2, u3), p2: one like (u2), p3: zero likes
		from .models import Reaction
		Reaction.objects.create(post=self.p1, user=u2, value=1)
		Reaction.objects.create(post=self.p1, user=u3, value=1)
		Reaction.objects.create(post=self.p2, user=u2, value=1)

		self.client.force_login(self.user)
		url = reverse('discussion') + '?sort=most_liked'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		posts = resp.context['posts']
		ordered = [p['post'].pk for p in posts]
		# Expect p1 (2 likes), p2 (1 like), p3 (0 likes)
		self.assertEqual(ordered, [self.p1.pk, self.p2.pk, self.p3.pk])
