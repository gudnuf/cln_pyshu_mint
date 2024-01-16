from coincurve import PrivateKey, PublicKey
from hashlib import sha256

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

l1 = "/usr/local/bin/lightning-cli --lightning-dir=/tmp/l1"
l2 = "/usr/local/bin/lightning-cli --lightning-dir=/tmp/l2"