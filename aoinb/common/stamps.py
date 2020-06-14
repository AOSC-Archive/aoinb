import collections
import configparser

import nacl.signing
import nacl.encoding
import nacl.exceptions


class Signer:
    def __init__(self, private_key: str):
        self.encoder = nacl.encoding.URLSafeBase64Encoder
        self.key = nacl.signing.SigningKey(
            private_key.encode('utf-8'), nacl.encoding.HexEncoder)

    def sign(self, data: bytes, detached=True) -> str:
        signed = self.key.sign(data, self.encoder)
        if detached:
            return signed.signature.decode('utf-8')
        else:
            return signed.decode('utf-8')


class Verifier:
    def __init__(self, key_store):
        self.key_store = key_store

    @classmethod
    def verify_with_key(cls, key: str, data: bytes, signature=None):
        encoder = nacl.encoding.URLSafeBase64Encoder
        vkey = nacl.signing.VerifyKey(
            key.encode('utf-8'), nacl.encoding.HexEncoder)
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(signature, str):
            signature = signature.encode('utf-8')
        try:
            return vkey.verify(data, signature, encoder)
        except nacl.exceptions.BadSignatureError:
            return None

    def verify(self, key_name: str, data: bytes, signature=None):
        return self.verify_with_key(self.key_store[key_name], data, signature)


class IniKeyStore(collections.UserDict):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.reload()

    def reload(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.filename, 'utf-8')
        self.data = dict(config['keys'])

    def __getitem__(self, key):
        self.reload()
        return super().__getitem__(key)
