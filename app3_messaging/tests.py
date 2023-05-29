import time
from unittest import TestCase

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import Client
from django.test.client import RequestFactory

from app3_messaging.views_messaging import internal_emailing, internal_emailing_mailbox


class RenderSendPage(TestCase):

    def setUp(self):
        self.client = Client()

    def test_internal_emailing(self):
        user = User.objects.filter(first_name='Didier', last_name="MEYRAND").first()
        factory = RequestFactory()
        request = factory.get(reverse('internal_emailing'))
        request.user = user
        request.session = self.client.session
        t = time.time()
        internal_emailing(request)
        d = time.time() - t
        print(f'>>> test_internal_emailing GET method passed in {round(d, 3)} seconds')
        data = {'group_recipients[]': ['3'], 'recipients[]': ['céline.barral', 'marie.bertrand',
                                                              'angelique.da-silva', 'sonia.dadamo',
                                                              'laurence.dode', 'claudette.ducros',
                                                              'laurent.dufour', 'dany.grillere',
                                                              'chantal.hugoud', 'anne-marie.leroy',
                                                              'hugo-bernard-joseph.meyrand',
                                                              'fatima.oudhebi',
                                                              'frederique.salvan', 'annick.teston'],
                'subject': 'test', 'tags_input': '[{"value":"tag1"}]', 'attachment': '', 'content': 'test',
                'envoidemessage': ''}
        request = factory.post(reverse('internal_emailing'), data=data)
        request.session = self.client.session
        request.user = user
        t = time.time()
        internal_emailing(request)
        d = time.time() - t
        print(f'>>> test_internal_emailing POST method passed in {round(d, 3)} seconds')

    def test_internal_emailing_answering(self):
        factory = RequestFactory()
        request = factory.post(reverse('internal_emailing'),
                               data={'convo_id': '4021', 'message_id': '4810', 'repondre': ''})
        request.user = User.objects.filter(first_name='Didier', last_name="MEYRAND").first()
        request.session = self.client.session
        t = time.time()
        internal_emailing_mailbox(request)
        d = time.time() - t
        print(f'>>> test_internal_emailing_answering passed in {round(d, 3)} seconds')
