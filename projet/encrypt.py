from cryptography.fernet import Fernet


def encrypt(message: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(message)


def decrypt(token: bytes, key: bytes) -> bytes:
    return Fernet(key).decrypt(token)

# ------ USAGE ------------------

# >>> key = Fernet.generate_key()
# >>> print(key.decode())
# GZWKEhHGNopxRdOHS4H4IyKhLQ8lwnyU7vRLrM3sebY=
# >>> message = 'John Doe'
# >>> encrypt(message.encode(), key)
# 'gAAAAABciT3pFbbSihD_HZBZ8kqfAj94UhknamBuirZWKivWOukgKQ03qE2mcuvpuwCSuZ-X_Xkud0uWQLZ5e-aOwLC0Ccnepg=='
# >>> token = _
# >>> decrypt(token, key).decode()
# 'John Doe'