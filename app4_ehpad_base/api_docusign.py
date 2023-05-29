# -*- coding: utf-8 -*-

""" https://developers.docusign.com/docs/esign-rest-api/esign101/status-and-error-codes/ """

import os
import jwt
import base64
import secrets
import logging
import requests

from app1_base.log import Logger

from django.conf import settings

from datetime import datetime, timedelta

from docusign_esign import EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients, \
    EnvelopesApi, RecipientViewRequest, ApiClient

# ----------------------------------------------------------------------------------------------------------------------


if 'log_error' not in globals():
    global log_error
    log_error = Logger('error', level=logging.ERROR).run()


# ----------------------------------------------------------------------------------------------------------------------


def get_url():
    """ The function creates the url for Docusign user to accept the consent for Serenicia  This operation is used
    only once, but is essential to avoid the following error 400 {“error”:”consent_required”} when Obtain the access token """

    url = settings.BASE_URI + "?response_type=" + \
          settings.RESPONSE_TYPE + "&scope=" + settings.SCOPE + \
          "&client_id=" + settings.CLIENT_ID_DOCUSIGN + "&state=" + \
          settings.STATE + "&redirect_uri=" + settings.SERENICIA_PATH

    return url


# ----------------------------------------------------------------------------------------------------------------------


def get_token():
    """ Create Json Web Token (JWT) and exchange it for an access token. Contained the data on authentication for Docusign request.
     Need Header, Body and signature for construct the JWT. https://jwt.io/ for verify the signature or jwt.decode. """

    jwt_token = jwt.encode(
        {
            'iss': settings.CLIENT_ID_DOCUSIGN,
            'sub': settings.USER_ID,
            'aud': settings.AUD,
            'iat': datetime.now(),  # JWT age
            'exp': datetime.now() + timedelta(minutes=30),  # Expiry date
            'scope': 'signature impersonation',
        },
        settings.PRIVATE_KEY, algorithm='RS256'
    )
    jwt.get_unverified_header(jwt_token)  # Decoded header

    try:
        jwt.decode(jwt_token, settings.PUBLIC_KEY,
                   options={
                       'verify_signature': True, 'verify_iss': True,
                       'verify_sub': True, 'verify_exp': True,
                       'verify_iat': True, 'verify_aud': True,
                   },
                   algorithms=['RS256'], audience=settings.AUD  # Decoded token
                   )

        assertion = jwt_token  # Information and Authentication for Docusign request

        # OBTAIN ACCESS TOKEN
        url_token = settings.URL_TOKEN
        data_token = {'grant_type': settings.GRANT_TYPE, 'assertion': assertion}
        response_token = requests.post(url=url_token, data=data_token)

        access_token = response_token.json()['access_token']  # Exchange JWT for access token
        return access_token

    #   <----- TOKEN ERROR ---------------------------------------------->
    except jwt.ExpiredSignatureError as e:
        log_error.error(f"Error JWT token check exp. {e}")  # JWT expired
        pass

    except jwt.InvalidSignatureError as e:
        log_error.error(f"Error JWT token check signature. {e}")  # JWT invalid
        pass

    except jwt.DecodeError as e:
        log_error.error(f"Error JWT token check signature. {e}")  # Invalid JWT options
        pass


# ----------------------------------------------------------------------------------------------------------------------


def get_account_id(access_token):
    """ Use access_token to get user information and return account_id. """

    header = {'Authorization': 'Bearer ' + access_token}  # Need space elif bad request
    response_user = requests.get(url=settings.URL_USER_INFO, headers=header)

    if response_user.status_code == 200:
        account_id = response_user.json()['accounts'][0]['account_id']
        return account_id

    else:
        log_error.error(f"Error get_account_id check {settings.URL_USER_INFO} or {header}.")


# ----------------------------------------------------------------------------------------------------------------------


def api_call(account_id, access_token):
    """ Use access_token and account_id for make an api call for future request. """

    header = {'Authorization': 'Bearer ' + access_token}  # Need space elif bad request
    response_api = requests.get(url=settings.API_CALL + account_id + '/brands', headers=header)

    if response_api.status_code == 200:
        return response_api.status_code, response_api.json()

    if response_api.status_code != 200:
        log_error.error(f"Error api_call check {header}.")


# ----------------------------------------------------------------------------------------------------------------------


def create_api_client(base_path, access_token):
    api_client = ApiClient()
    api_client.host = base_path
    api_client.set_default_header("Authorization", "Bearer " + access_token)
    return api_client


# ----------------------------------------------------------------------------------------------------------------------


class Signature:
    """ Class method for use Docusign api. """

    @staticmethod
    def get_arguments(ln_fn, email):
        """ Create envelope arguments and user arguments who use for signing documents. """

        access_token = get_token()
        account_id = get_account_id(access_token)
        signer_user_id = base64.b64encode((ln_fn + email).encode('utf-8')).decode('utf-8')

        envelope_args = {
            'signer_name': ln_fn, 'signer_email': email,
            'signer_user_id': signer_user_id, 'return_url': settings.PUBLIC_SITE + '/documents/signed/',
        }
        args = {
            'access_token': access_token, 'base_path': settings.URL_API_CLIENT,
            'account_id': account_id, 'envelope_args': envelope_args
        }
        return args

    @classmethod
    def post_envelope(cls, args):
        """ Create and sent the envelope with document for sign. redirect_url = url for sign. """

        envelope_args = args['envelope_args']
        envelope_definition = cls.make_envelope(envelope_args)

        api_client = create_api_client(base_path=args['base_path'], access_token=args['access_token'])

        envelope_api = EnvelopesApi(api_client)
        results = envelope_api.create_envelope(account_id=args['account_id'], envelope_definition=envelope_definition)

        envelope_id = results.envelope_id
        args['envelope_id'] = envelope_id

        recipient_view_request = RecipientViewRequest(
            authentication_method='email',
            client_user_id=envelope_args['signer_user_id'],
            recipient_id='1',
            return_url=envelope_args['return_url'],
            user_name=envelope_args['signer_name'],
            email=envelope_args['signer_email'],
        )

        results = envelope_api.create_recipient_view(
            account_id=args['account_id'],
            envelope_id=envelope_id,
            recipient_view_request=recipient_view_request,
        )

        url = results.url
        return {'envelope_id': envelope_id, 'redirect_url': url,
                'doc_list': [doc.document_id for doc in envelope_definition.documents]}

    @classmethod
    def make_envelope(cls, args):
        query_doc = args['document']
        doc_list = []

        for doc in query_doc:
            doc_id = int.from_bytes(secrets.token_bytes(2), 'little')

            with open(os.path.join(settings.MEDIA_ROOT, doc.file.name), 'rb') as file:
                content_bytes = file.read()
            doc_b64 = base64.b64encode(content_bytes).decode('utf-8')

            doc_list.append(Document(
                document_base64=doc_b64,
                name=doc.document_type,
                file_extension='pdf',
                document_id=doc_id,
            ))

        signer = Signer(
            email=args['signer_email'],
            name=args['signer_name'],
            recipient_id='1',
            routing_order='1',
            client_user_id=args['signer_user_id'],
        )

        sign_here = SignHere(
            anchor_string='/sn1/',
            anchor_units='pixels',
            anchor_y_offset='10',
            anchor_x_offset='20',
        )

        signer.tabs = Tabs(sign_here_tabs=[sign_here])
        envelope_definition = EnvelopeDefinition(
            email_subject='Please sign this document.',
            documents=doc_list,
            recipients=Recipients(signers=[signer]),
            status='sent',
        )
        return envelope_definition

    @staticmethod
    def list_document(args):
        api_client = create_api_client(base_path=args['base_path'], access_token=args['access_token'])
        envelope_api = EnvelopesApi(api_client)
        list_doc = envelope_api.list_documents(account_id=args['account_id'], envelope_id=args['envelope_id'])
        return list_doc

    @staticmethod
    def save_envelope_documents(list_doc, args):
        standard_doc_item = [
            {'name': 'Combined',
             'type': 'content', 'document_id': 'combined'
             }
        ]
        # list(map(lambda)) function return new list with new value.
        envelope_doc_items = list(map(lambda doc:
                                      ({'document_id': doc.document_id, 'name': 'Certificate of completion',
                                        'type': doc.type})
                                      if (doc.document_id == 'certificate') else
                                      ({'document_id': doc.document_id, 'name': doc.name,
                                        'type': doc.type}),
                                      list_doc.envelope_documents))
        envelope_documents = {
            'envelope_id': args['envelope_id'],
            'envelope_documents': standard_doc_item + envelope_doc_items
        }
        args['envelope_documents'] = envelope_documents

    @staticmethod
    def download_document(args):
        api_client = create_api_client(base_path=args['base_path'], access_token=args['access_token'])
        envelope_api = EnvelopesApi(api_client)
        document_id = args['document_id']

        temp_file = envelope_api.get_document(
            account_id=args['account_id'],
            document_id=document_id,
            envelope_id=args['envelope_id']
        )
        return {'data': temp_file}
