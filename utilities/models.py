from typing import List
from .mint import Keyset


class MintQuote():

    def __init__(self, quote_id: str, request: str, paid: bool, expiry: str,):
        self.request = request
        self.quote_id = quote_id
        self.paid = paid
        self.expiry = expiry


class BlindedSignature():
    """
    Blinded signature or "promise" which is the signature on a `BlindedMessage`

    Defined in NUT-00: https://github.com/cashuBTC/nuts/blob/main/00.md#blindsignature
    """

    def __init__(self, keyset_id: str, amount: int, signature: str):
        self.keyset_id = keyset_id
        self.amount = amount
        self.signature = signature

    def to_json(self):
        return {
            "id": self.keyset_id,
            "amount": self.amount,
            "C_": self.signature,
        }


class Keyset():
    """
    Model for a populated keyset
    """

    def __init__(self, keyset: Keyset):
        self.keyset = keyset

    def to_json(self):
        return {
            "id": self.keyset.id,
            "unit": 'sat',
            "keys": self.keyset.public_keys_hex,
        }


class GetKeysResponse():
    """
      Response for `GET /keys` defined in NUT-01
      https://github.com/cashubtc/nuts/blob/main/01.md#example
    """

    def __init__(self, keyset: Keyset):
        self.keyset = keyset

    def to_json(self):
        if not self.keyset:
            return {
                "keysets": []
            }
        return {
            "keysets": [
                Keyset(self.keyset).to_json()
            ]
        }


class KeysetMeta():
    """
    Model for a keyset metadata
    """

    def __init__(self, keyset: Keyset):
        self.keyset = keyset

    def to_json(self):
        return {
            "id": self.keyset.id,
            "unit": 'sat',
            "active": True
        }


class GetKeysetsResponse():
    """
      Response for `GET /keysets` defined in NUT-02
      https://github.com/cashubtc/nuts/blob/main/02.md#example-response
    """

    def __init__(self, keysets: list):
        self.keysets = keysets

    def to_json(self):
        return {"keysets": [KeysetMeta(ks).to_json() for ks in self.keysets]}


class PostQuoteMintResponse():
    """
    Response for `POST /v1/mint/quote/bolt11` defined in NUT-04
    https://github.com/cashubtc/nuts/blob/main/04.md#mint-quote 
    """

    def __init__(self, quote: str, request: str, paid: bool, expiry: str):
        self.quote = quote
        self.request = request
        self.paid = paid
        self.expiry = expiry

    def to_json(self):
        return {
            "quote": self.quote,
            "request": self.request,
            "paid": self.paid,
            "expiry": self.expiry
        }


class PostMintResponse():
    """
    Response for `POST /v1/mint/bolt11` defined in NUT-04
    https://github.com/cashubtc/nuts/blob/main/04.md#minting-tokens
    """

    def __init__(self, sigs: List[BlindedSignature]):
        self.blinded_signatures = sigs

    def to_json(self):
        return {
            "signatures": [sig for sig in self.blinded_signatures]
        }


class PostQuoteMeltResponse():
    """
    Response for `POST /v1/melt/quote/bolt11` defined in NUT-05
    https://github.com/cashubtc/nuts/blob/main/05.md#melt-quote
    """

    def __init__(self, quote: str, amount: str, fee_reserve: int, paid: bool, expiry: int = None):
        self.quote = quote
        self.amount = amount
        self.fee_reserve = fee_reserve
        self.paid = paid
        self.expiry = expiry

    def to_json(self):
        return {
            "quote": self.quote,
            "amount": self.amount,
            "fee_reserve": self.fee_reserve,
            "paid": self.paid,
            "expiry": self.expiry
        }


class PostMeltResponse():
    """
    Response for `POST /v1/melt/bolt11` defined in NUT-05
    https://github.com/cashubtc/nuts/blob/main/05.md#melting-tokens
    """

    def __init__(self, paid: bool, preimage: str = None):
        self.paid = paid
        self.preimage = preimage

    def to_json(self):
        return {
            "paid": self.paid,
            "preimage": self.preimage
        }


class PostSwapResponse(PostMintResponse):
    """
    Response for `POST /v1/swap` defined in NUT-03
    https://github.com/cashubtc/nuts/blob/main/03.md
    """
