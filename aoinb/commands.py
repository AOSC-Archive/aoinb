"""
Tool commands
"""

import nacl.signing
import nacl.encoding


def generate_keypair():
    encoder = nacl.encoding.HexEncoder
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    signing_key_str = signing_key.encode(encoder=encoder).decode('utf-8')
    verify_key_str = verify_key.encode(encoder=encoder).decode('utf-8')
    return verify_key_str, signing_key_str


def generate_keypair_config():
    pubkey, privkey = generate_keypair()
    s = "[key]\npublic = %s\nprivate = %s\n" % (pubkey, privkey)
    return s


def cmd_build(args):
    pass


def cmd_genkey(args):
    print(generate_keypair_config())
