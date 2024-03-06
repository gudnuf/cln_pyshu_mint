import time
import json
import math
from pyln.client import Millisatoshi
from typing import List, Dict
from hashlib import sha256
from coincurve import PublicKey, PrivateKey
from .rpc_plugin import plugin
from .crypto import random_hash, blind_sign
from .utils import ISSUED_TOKEN_KEY_BASE, MELT_QUOTE_KEY_BASE


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

    def _generate_promise(self, output: List[Dict[str, str]]):
        k = self.keyset.private_keys[int(output["amount"])]
        B_ = output["B_"]
        C_ = blind_sign(B_, k)
        return BlindedSignature(
            keyset_id=self.keyset.id,
            amount=int(output["amount"]),
            signature=C_.format().hex()
        )

    def _generate_promises(self, outputs: List[Dict[str, str]]):
        promises: List[BlindedSignature] = []

        for output in outputs:
            promises.append(self._generate_promise(output))

        return promises

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
            amount_sat=amount_sat,
            request=bolt11,
            paid=False,
            expiry=expires_at
        )

    def get_mint_quote(self, quote: str):
        mint_invoice = self.get_invoice(quote)

        return MintQuote(
            quote_id=quote,
            amount_sat=mint_invoice.amount_msat // 1000,
            request=mint_invoice.bolt11,
            paid=mint_invoice.paid,
            expiry=mint_invoice.expires_at
        )

    def mint_tokens(self, outputs: List[Dict[str, str]], quote_id: str):
        requested_amount = sum([int(b["amount"]) for b in outputs])
        quote = self.get_mint_quote(quote_id)

        assert quote.paid, "Quote not paid"
        assert not quote.was_issued(), "Tokens already issued for this quote"
        assert requested_amount == quote.amount_sat, "amount to mint does not match quote amount"
        if quote.expiry:
            assert quote.expiry > int(time.time()), "Quote expired"

        promises = self._generate_promises(outputs)

        quote.mark_quote_issued()

        return promises

    def melt_quote(self, bolt11: str):
        # TODO: look to see if a quote already exists for this bolt11
        
        amount_msat = Millisatoshi(
            plugin.rpc.decodepay(bolt11).get("amount_msat"))
        amount_sat = math.floor(amount_msat.to_satoshi())
        quote_id = random_hash()
        fee_reserve = 0
        expiry = None

        return MeltQuote(
            quote_id=quote_id,
            amount_sat=amount_sat,
            fee_reserve=fee_reserve,
            paid=False,
            expiry=expiry,
            request=bolt11
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

    def __init__(self, quote_id: str, amount_sat: int, request: str, paid: bool, expiry: str,):
        self.request = request
        self.quote_id = quote_id
        self.paid = paid
        self.expiry = expiry
        self.amount_sat = amount_sat

    def mark_quote_issued(self):
        """
        Store the quote_id in the datastore to prevent issuing tokens for the same quote
        """

        key = ISSUED_TOKEN_KEY_BASE.copy()
        key.append(self.quote_id)
        plugin.rpc.datastore(key=key, string="")

    def was_issued(self):
        """ Check if the quote exists in the datastore """
        key = ISSUED_TOKEN_KEY_BASE.copy()
        key.append(self.quote_id)
        return plugin.rpc.listdatastore(key=key)["datastore"] != []


class MeltQuote():
    def __init__(self, quote_id: str, amount_sat: str, fee_reserve: int, paid: bool, request: str, expiry: int = None):
        self.quote_id = quote_id
        self.amount_sat = amount_sat
        self.fee_reserve = fee_reserve
        self.paid = paid
        self.request = request
        self.expiry = expiry

    @staticmethod
    def from_db_string(db_string: str):
        try:
            data = json.loads(db_string)
            return MeltQuote(
                quote_id=data["quote"],
                amount_sat=data["amount"],
                fee_reserve=data["fee_reserve"],
                paid=data["paid"],
                request=data["request"],
                expiry=data["expiry"]
            )
        except Exception:
            raise ValueError("Failed to parse quote from db string")

    @staticmethod
    def find(quote_id: str):
        """ Look for a melt quote in the datastore """

        key = MELT_QUOTE_KEY_BASE.copy()
        key.append(quote_id)

        data = plugin.rpc.listdatastore(key=key)["datastore"]
        assert len(data) != 0, "Quote not found"

        quote = MeltQuote.from_db_string(data[0].get("string", None))
        assert quote, "Quote not found"

        return quote

    def to_json(self):
        return {
            "quote": self.quote_id,
            "amount": self.amount_sat,
            "fee_reserve": self.fee_reserve,
            "paid": self.paid,
            "request": self.request,
            "expiry": self.expiry
        }

    def save(self, mode="must-create"):
        """ Store the quote data in the datastore """

        key = MELT_QUOTE_KEY_BASE.copy()
        key.append(self.quote_id)
        plugin.rpc.datastore(
            key=key, string=json.dumps(self.to_json()), mode=mode)

    def update(self):
        """ Update the quote in the datastore """

        self.save(mode="must-replace")


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
