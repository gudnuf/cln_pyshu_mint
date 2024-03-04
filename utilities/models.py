from typing import List, Dict
from hashlib import sha256
from coincurve import PublicKey, PrivateKey
from .rpc_plugin import plugin
from .crypto import random_hash


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

    def generate_invoice(self, amount_msat: int, quote_id: str):
        invoice = plugin.rpc.invoice(
            amount_msat=amount_msat,
            label=f'cashu:{quote_id}',
            description="Cashu mint request"
        )

        if invoice.get("bolt11") == None:
            raise ValueError("failed to generate invoice")
        else:
            return invoice.get("bolt11"), invoice.get("expires_at")

    def get_invoice(self, quote_id: str):
        """
        find invoice with label of `cashu:{quote_id}`

        Raises: 
            Exception: Invoice not found
        """

        invoices = plugin.rpc.listinvoices(
            label=f'cashu:{quote_id}').get("invoices", [])

        assert len(invoices) == 1, "Quote not found"

        return Invoice(rpc_invoice=invoices[0])

    def mint_quote(self, amount_sat: int):
        # TODO: add a max peg in
        # TODO: add a max balance for the the mint

        amount_msat = amount_sat * 1000
        quote_id = random_hash()

        bolt11, expires_at = self.generate_invoice(
            amount_msat, quote_id)

        return MintQuote(
            quote_id=quote_id,
            request=bolt11,
            paid=False,
            expiry=expires_at
        )

    def get_mint_quote(self, quote: str):
        mint_invoice = self.get_invoice(quote)

        return MintQuote(
            quote_id=quote,
            request=mint_invoice.bolt11,
            paid=mint_invoice.paid,
            expiry=mint_invoice.expires_at
        )


class Invoice():

    def __init__(self, rpc_invoice: dict):
        bolt11 = rpc_invoice.get("bolt11", None)
        status = rpc_invoice.get("status", None)
        expires_at = rpc_invoice.get("expires_at", None)
        amount_msat = rpc_invoice.get("amount_msat", None)

        assert bolt11 is not None, "bolt11 is required"
        assert status is not None, "status is required"
        assert expires_at is not None, "expires_at is required"
        assert amount_msat is not None, "amount_msat is required"

        self.bolt11 = bolt11
        self.paid = status == "paid"
        self.expires_at = expires_at
        self.amount_msat = amount_msat


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


class KeysKeyset():
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
                KeysKeyset(self.keyset).to_json()
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
