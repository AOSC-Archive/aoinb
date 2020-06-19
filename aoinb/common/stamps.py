import time
import typing
import secrets
import collections
import configparser

import nacl.hashlib
import nacl.signing
import nacl.encoding
import nacl.exceptions


class RawSignature(typing.NamedTuple):
    time_ms: int
    data_hash: bytes

    def dumps(self):
        return self.time_ms.to_bytes(8, 'little') + self.data_hash

    @classmethod
    def loads(cls, data: bytes):
        return cls(int.from_bytes(data[:8], 'little'), data[8:])

    @classmethod
    def from_bytes(cls, data: bytes):
        time_ms = int(time.time() * 1000)
        hashed = nacl.hashlib.blake2b(data).digest()
        return cls(time_ms, hashed)

    @classmethod
    def from_file(cls, fp):
        time_ms = int(time.time() * 1000)
        hasher = nacl.hashlib.blake2b()
        for block in iter(lambda: fp.read(4096), b''):
            hasher.update(block)
        return cls(time_ms, hasher.digest())

    @classmethod
    def from_data(cls, data):
        if isinstance(data, str):
            return cls.from_bytes(data.encode('utf-8'))
        elif isinstance(data, bytes):
            return cls.from_bytes(data)
        else:
            return cls.from_file(data)


class Signer:
    def __init__(self, private_key: str):
        self.encoder = nacl.encoding.URLSafeBase64Encoder
        self.key = nacl.signing.SigningKey(
            private_key.encode('utf-8'), nacl.encoding.HexEncoder)

    def sign_raw(self, data: bytes) -> str:
        signed = self.key.sign(data, self.encoder)
        return signed.signature.decode('utf-8')

    def sign(self, data) -> str:
        payload = RawSignature.from_data(data).dumps()
        return self.sign_raw(payload)


class Verifier:
    def __init__(self, key_store):
        self.key_store = key_store

    @classmethod
    def verify_with_key(cls, key: str, data, signature: str, ttl=None) -> bool:
        encoder = nacl.encoding.URLSafeBase64Encoder
        vkey = nacl.signing.VerifyKey(
            key.encode('utf-8'), nacl.encoding.HexEncoder)
        try:
            signature = encoder.decode(signature.encode('utf-8'))
        except ValueError:
            return False
        hashed = nacl.hashlib.blake2b(data).digest()
        try:
            payload = vkey.verify(hashed, signature)
        except nacl.exceptions.BadSignatureError:
            return False
        sig_recv = RawSignature.loads(payload)
        if ttl is not None and sig_recv.time_ms/1000 + ttl < time.time():
            return False
        sig_data = RawSignature.from_data(data)
        return secrets.compare_digest(sig_recv.data_hash, sig_data.data_hash)

    def verify(self, key_name: str, data, signature: str, ttl=None) -> bool:
        try:
            key = self.key_store[key_name]
        except KeyError:
            return False
        return self.verify_with_key(key, data, signature, ttl)


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
