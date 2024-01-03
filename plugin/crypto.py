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