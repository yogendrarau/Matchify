from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Friendship, Message

User = get_user_model()

class ChatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = User.objects.create_user(username='alice', password='pass')
        self.u2 = User.objects.create_user(username='bob', password='pass')
        # create friendship
        Friendship.objects.create(user1=self.u1, user2=self.u2)

    def test_send_and_get_messages_happy_path(self):
        self.client.login(username='alice', password='pass')
        # send message
        resp = self.client.post(f'/chat/{self.u2.username}/send', {'content': 'hello bob'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        mid = data.get('message_id')
        # get messages
        resp2 = self.client.get(f'/chat/{self.u2.username}/messages')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2.get('success'))
        msgs = data2.get('messages')
        self.assertTrue(any(m['id'] == mid for m in msgs))

    def test_send_message_unauthorized(self):
        other = User.objects.create_user(username='charlie', password='pass')
        self.client.login(username='alice', password='pass')
        resp = self.client.post(f'/chat/{other.username}/send', {'content': 'hi'})
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertFalse(data.get('success'))

