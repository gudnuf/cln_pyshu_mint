from typing import Dict
from hashlib import sha256
from coincurve import PublicKey, PrivateKey

# settings should have (see, max_order, and derivation_path)
SettingsDict = Dict

class KeySet:
    def __init__(self, settings: SettingsDict):
        self.private_keys = self.generate_private_keyset(settings["seed"], 
            settings["MAX_ORDER"], 
            settings["derivation_path"]) # TODO make private_keys only readable by this class
        
        self.public_keys = self.get_public_keys()

        self.id = self.get_id()

    def generate_private_keyset(self, seed, MAX_ORDER: int, derivation_path):
        to_hash = [(seed + derivation_path + str(i)).encode() for i in range(MAX_ORDER)]
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
