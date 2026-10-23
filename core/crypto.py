import base64
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

ENC_V1 = 'ENC::'
ENC_V2 = 'ENC2::'


def is_encrypted(value):
    return bool(value) and (value.startswith(ENC_V1) or value.startswith(ENC_V2))


def _configured_keys():
    primary = settings.FIELD_ENCRYPTION_KEY
    configured = list(getattr(settings, 'FIELD_ENCRYPTION_KEYS', ()) or ())
    # override_settings(FIELD_ENCRYPTION_KEY=...) debe sustituir también el
    # anillo cargado al iniciar el proceso de pruebas.
    if not configured or configured[0] != primary:
        configured = [primary] if primary else []
    return configured


def _fernets():
    keys = _configured_keys()
    if not keys:
        raise RuntimeError('FIELD_ENCRYPTION_KEY no está configurada')
    try:
        return [Fernet(key.encode('ascii')) for key in keys]
    except Exception as exc:
        raise RuntimeError('FIELD_ENCRYPTION_KEYS contiene una clave Fernet inválida') from exc


def _fernet():
    return MultiFernet(_fernets())


def _legacy_key_bytes():
    key = settings.LEGACY_DJANGO_SECRET_KEY or settings.SECRET_KEY
    return key.encode('utf-8')


def encrypt_val(value: str) -> str:
    if not value or is_encrypted(value):
        return value
    token = _fernet().encrypt(value.encode('utf-8')).decode('ascii')
    return ENC_V2 + token


def _decrypt_legacy(value: str) -> str:
    raw_b64 = value[len(ENC_V1):]
    encrypted = base64.b64decode(raw_b64.encode('utf-8'))
    key = _legacy_key_bytes()
    decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)])
    return decrypted.decode('utf-8')


def decrypt_val(value: str) -> str:
    if not value:
        return value
    if value.startswith(ENC_V2):
        try:
            return _fernet().decrypt(value[len(ENC_V2):].encode('ascii')).decode('utf-8')
        except InvalidToken as exc:
            raise ValueError('No fue posible descifrar el secreto ENC2') from exc
    if value.startswith(ENC_V1):
        return _decrypt_legacy(value)
    return value


def migrate_value(value: str) -> str:
    if not value or value.startswith(ENC_V2):
        return value
    plaintext = decrypt_val(value)
    return encrypt_val(plaintext)


def needs_rotation(value: str) -> bool:
    if not value or not value.startswith(ENC_V2):
        return bool(value)
    token = value[len(ENC_V2):].encode('ascii')
    try:
        _fernets()[0].decrypt(token)
        return False
    except InvalidToken:
        try:
            _fernet().decrypt(token)
            return True
        except InvalidToken as exc:
            raise ValueError('No fue posible descifrar el secreto ENC2') from exc


def rotate_value(value: str) -> str:
    if not value:
        return value
    if not value.startswith(ENC_V2):
        return migrate_value(value)
    token = value[len(ENC_V2):].encode('ascii')
    try:
        rotated = _fernet().rotate(token).decode('ascii')
    except InvalidToken as exc:
        raise ValueError('No fue posible rotar el secreto ENC2') from exc
    return ENC_V2 + rotated
