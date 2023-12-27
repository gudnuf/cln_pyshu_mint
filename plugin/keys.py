from typing import Dict
from hashlib import sha256
from base64 import b64encode
from coincurve import PublicKey, PrivateKey
import math

PrivKeyset = Dict[int, PrivateKey]
PubKeyset = Dict[int, PublicKey]

def generate_private_keyset(seed, MAX_ORDER: int, derivation_path):
    to_hash = [(seed + derivation_path + str(i)).encode() for i in range(MAX_ORDER)]
    return {
        2 ** idx: PrivateKey(
            sha256(to_hash).digest()[:32]
        )
        for idx, to_hash in enumerate(to_hash)
    }

def get_keyset(priv_keyset: PrivKeyset):
    pub_keyset: PubKeyset = {}
    for idx, pk in priv_keyset.items():
        pub_keyset[idx] = pk.public_key
    id = derive_keyset_id(pub_keyset)
    return pub_keyset, id

