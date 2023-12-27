from coincurve import PrivateKey, PublicKey

# https://github.com/cashubtc/nuts/blob/main/00.md#blind-diffie-hellmann-key-exchange-bdhke
def blind_sign(B_, k: PrivateKey): 
    # B_ = Y + rG with r being a random blinding factor (blinding)
    # C_ = kB_ (these two steps are the DH key exchange) (signing)
    B_bytes = bytes.fromhex(B_)
    C_ = PublicKey(B_bytes).multiply(k.secret)
    return C_