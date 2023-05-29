import jwt
import requests
from django.conf import settings


def sign_data(data: dict, key: bytes):
    """
    Sign JSON serializable data with private key
    :param data: JSON serializable data
    :param key: local RSA private key
    :return: Dict with signed data in bytes
    """
    signed_data = jwt.encode(data, key, algorithm=settings.RSA_ALGO_KEY)
    if type(signed_data) is bytes:
        signed_data = signed_data.decode('UTF-8')
    return {'signed': signed_data}


def encode_data(data: dict):
    """
    Encode JSON serializable data with symmetric encoding
    :param data: JSON serializable data
    :return: bytes of data with symmetric encoding
    """
    return jwt.encode(data, settings.PORTAL_SYM_KEY, algorithm=settings.PORTAL_SYM_ALGO)


def verify_signature(signed_data: dict, key: bytes):
    """
    Verify the data's signature
    :param signed_data: received decoded data
    :param key: public key of the external site
    :return: verified data
    """
    return jwt.decode(bytes(signed_data.get('signed'), 'UTF-8'), key, algorithms=settings.RSA_ALGO_KEY)


def decode_data(data: bytes):
    """
    Decodes bytes data with symmetric encoding
    :param data: received bytes data
    :return: decoded data
    """
    return jwt.decode(data, settings.PORTAL_SYM_KEY, algorithms=settings.PORTAL_SYM_ALGO)


def get_response(url: str, timeout: [float, int], key: bytes):
    """
    Get dict of data from an external URL with RSA encoding
    :param key: public key of the external URL
    :param url: requested external URL
    :param timeout: float -> 1 = 1 second
    :return: dict of received data in case of success, empty dict if error or bad response
    """
    result = {}
    try:
        res = requests.get(url, timeout=timeout)
        if res.status_code == 200:
            decoded_data = decode_data(res.content)
            result = verify_signature(decoded_data, key)
    except (requests.exceptions.RequestException, jwt.InvalidSignatureError):
        pass
    return result


def post_message(url: str, timeout: [float, int], message: dict, key: bytes):
    """
    Post encoded dict to external URL
    :param key: local private key
    :param url: URL to send data
    :param timeout: float -> 1 = 1 second
    :param message: JSON serializable data
    :return: True in case of success, False if error or bad response
    """
    try:
        signed_data = sign_data(message, key)
        encoded_data = {'data': encode_data(signed_data)}
        res = requests.post(url, data=encoded_data, timeout=timeout)
        if res.status_code == 200:
            return res.content
    except requests.exceptions.RequestException:
        pass
    return False
