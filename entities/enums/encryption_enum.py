from enum import StrEnum


class EncryptionEnum(StrEnum):
    SSL = 'ssl'
    TLS = 'tls'
    STARTLS = 'startls'
