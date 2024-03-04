import random
import base64
from coincurve import PrivateKey, PublicKey
from hashlib import sha256

# https://github.com/cashubtc/nuts/blob/main/00.md#blind-diffie-hellmann-key-exchange-bdhke
def blind_sign(B_, k: PrivateKey): 
    # B_ = Y + rG with r being a random blinding factor (blinding)
    # C_ = kB_ (these two steps are the DH key exchange) (signing)
    B_bytes = bytes.fromhex(B_)
    C_ = PublicKey(B_bytes).multiply(k.secret)
    return C_

# TODO: figure a better way to generate the quote
def generate_quote():
    return sha256(PrivateKey().secret).hexdigest()[0:16]


def random_hash() -> str:
    """Returns a base64-urlsafe encoded random hash."""
    return base64.urlsafe_b64encode(
        bytes([random.getrandbits(8) for i in range(30)])
    ).decode()


def hash_to_curve(x_bytes):
    # Hash the secret using SHA-256
    hash_value = sha256(x_bytes).digest()
    # Create a public key Y from the hashed secret
    Y = PublicKey.from_secret(hash_value)
    return Y

def verify_token(C, secret_bytes, k: PrivateKey):
    # k*hash_to_curve(x) == C
    Y = hash_to_curve(secret_bytes)
    kY = Y.multiply(k.secret)
    return kY.format().hex() == C
