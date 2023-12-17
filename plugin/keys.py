from hashlib import sha256
from coincurve import PublicKey, PrivateKey


def generate_private_keyset(seed, MAX_ORDER, derivation_path):
    to_hash = [(seed + derivation_path + str(i)).encode() for i in range(MAX_ORDER)]
    return {
        2 ** idx: PrivateKey(
            sha256(to_hash).digest()[:32]
        )
        for idx, to_hash in enumerate(to_hash)
    }

def get_keyset(priv_keyset):
    pub_keyset = {}
    for idx, pk in priv_keyset.items():
        pub_keyset[idx] = pk.public_key
    return pub_keyset