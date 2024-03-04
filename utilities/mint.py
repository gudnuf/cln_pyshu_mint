from typing import Dict
from hashlib import sha256
from coincurve import PublicKey, PrivateKey


class Keyset:

    id: str
    private_keys: Dict[int, PrivateKey]
    public_keys: Dict[int, PublicKey]
    active: bool

    def __init__(self, derivation_path: str,  seed: str, max_order: int):
        self.seed = seed
        self.derivation_path = derivation_path
        self.max_order = max_order
        self.generate_keys()
        self.id = self.get_id()

    @property
    def public_keys_hex(self) -> Dict[int, str]:
        assert self.public_keys, "public keys not set"
        return {
            int(amount): key.format().hex()
            for amount, key in self.public_keys.items()
        }

    def generate_keys(self):
        self.private_keys = self.generate_private_keyset()
        self.public_keys = self.get_public_keys()

    def generate_private_keyset(self):
        to_hash = [(self.seed + self.derivation_path + str(i)).encode()
                   for i in range(self.max_order)]
        return {
            2 ** idx: PrivateKey(
                sha256(to_hash).digest()[:32]
            )
            for idx, to_hash in enumerate(to_hash)
        }

    def get_public_keys(self):
        pub_keyset: Dict[int, PublicKey] = {}
        for idx, pk in self.private_keys.items():
            pub_keyset[idx] = pk.public_key
        return pub_keyset

    def get_id(self):
        sorted_keys = dict(sorted(self.public_keys.items()))
        pubkeys_concat = b"".join([p.format() for p in sorted_keys.values()])
        return "00" + sha256(pubkeys_concat).hexdigest()[:14]


class Mint:
    def __init__(self, derivation_path: str, seed: str, max_order: int):
        self.keyset = Keyset(derivation_path, seed, max_order)
