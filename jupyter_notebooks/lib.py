from coincurve import PrivateKey, PublicKey
from hashlib import sha256
import json

def hash_to_curve(x_bytes):
    # Hash the secret using SHA-256
    hash_value = sha256(x_bytes).digest()
    # Create a public key Y from the hashed secret
    Y = PublicKey.from_secret(hash_value)
    return Y

def subtract_points(pt1: PublicKey, pt2:  PublicKey):
    p = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    x2, y2 = pt2.point()
    neg_pt2 = PublicKey.from_point(x2, (p - y2) % p)
    difference = PublicKey.combine_keys([pt1, neg_pt2])
    return difference

def generate_blinded_messages(secrets, amounts):
    assert len(secrets) == len(amounts)
    BlindedMessages =  []
    rs = []
    for s, amount in zip(secrets, amounts):
        # r is a random blinding factor
        r = PrivateKey()
        R = r.public_key
        #Y = hash_to_curve(x)
        Y = hash_to_curve(s.encode())
        # B_ = Y + rG
        B_ = PublicKey.combine_keys([Y, R]).format().hex()
        BlindedMessages.append({"amount": amount, "B_": B_})
        rs.append(r.secret)
    return BlindedMessages, rs

def verify_token(C, secret_bytes, k: str):
    # k*hash_to_curve(x) == C
    Y = hash_to_curve(secret_bytes)
    kY = Y.multiply(bytes.fromhex(k))
    return kY.format().hex() == C

def construct_token(C_: PublicKey, K: bytes, r: str):
    rK = PublicKey(K).multiply(r)
    # C = C_ - rK
    C = subtract_points(C_, rK)
    return C.format().hex()

def construct_inputs(blinded_sigs, rs, secrets, pubkeys, privkeys):
    inputs = []
    for output, r, s in zip(blinded_sigs, rs, secrets):
        amount = output["amount"]
        # K is the public key for this token value
        K = bytes.fromhex(pubkeys.get(str(amount)))
        # C_ is blinded signature
        C_ = PublicKey(bytes.fromhex(output["C_"]))
        # C is unblinded signature
        C = construct_token(C_, K, r)
        assert verify_token(C, s.encode(), privkeys.get(str(amount)))
        inputs.append({
            "amount": amount,
            "C": C,
            "id": output["id"],
            "secret": s
        })
    return json.dumps(inputs)
