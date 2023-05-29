from django.core.management.base import BaseCommand
import unittest
from django.test import Client
from django.test.client import RequestFactory
from django.contrib.auth.models import Group, User
from app3_messaging.middleware import middleware_msg_notif
import time
import asyncio


class Command(BaseCommand):
    help = """
    If you need Arguments, please check other modules in 
    django/core/management/commands.
    """

    def handle(self, **options):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestChronology)
        unittest.TextTestRunner().run(suite)


class TestChronology(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    async def get_response(self, request):
        return f'-- Allright --'

    def test_middelware_message(self):
        """
                Tests that the middelware calcutaion for unread message and old message are not too long
        """
        print(f'------------------------------------ TEST MESSAGE MIDDLEWARE -----------------------------------------')
        try:
            factory = RequestFactory()
            request = factory.get('/')        # or any other methods
            request.user = User.objects.filter(first_name='Didier', last_name="MEYRAND").first()
            request.session = self.client.session
            middleware = middleware_msg_notif(self.get_response)
            t = time.time()
            asyncio.run(middleware(request))
            d = time.time()-t
            print(f'>>> test_middelware_message passed in {d} seconds')
        except Exception as ex:
            self.fail(f'EXCEPTION IN test_middelware_message')

    def test_equality(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        # from core.models import Yourmodel
        self.failUnlessEqual(1 + 1, 2)
