#!/usr/bin/env python3

from typing import Dict
from coincurve import PublicKey
from pyln.client import Plugin
import keys
import  crypto

plugin = Plugin()

plugin.keys: keys.PrivKeyset
plugin.keysetId = ""
plugin.melt_quotes: Dict[str, Dict] = {}

plugin.add_option(name="path",
                  default="/0/0/0/0",
                  description="Derivation path for current keyset")

plugin.add_option(name="max_order",
                  default="64",
                  description="Determines values the mint supports")

@plugin.init()
def init(options, configuration, plugin):
    seed = "johnny apple"
    plugin.keys = keys.generate_private_keyset(
        seed,
        int(options['max_order'], 10),
        options["path"]
    )
    _, id = keys.get_keyset(plugin.keys)
    plugin.keysetId = id

# https://github.com/cashubtc/nuts/blob/main/01.md#nut-01-mint-public-key-exchange
# GET /keys
@plugin.method("cashu-get-keys")
def get_keys(plugin: Plugin):
    """Returns the public keyset of the mint"""
    pub_keyset, id = keys.get_keyset(plugin.keys)
    return {
            "keysets": [
                {
                    "id": id,
                    "unit": 'sat',
                    "keys": {
                        key: value.format().hex() for key, value in pub_keyset.items()
                        },
                }
            ]
        }

# https://github.com/cashubtc/nuts/blob/main/02.md#multiple-keysets
# GET /keysets & GET /keyset/{keysetId}
@plugin.method("cashu-get-keysets")
def get_keysets(plugin: Plugin, keyset_id=None):
    """Returns all keysets of the mint"""
    if (keyset_id):
        return "Not implemented" # TODO: return just the requested keyset
    else:
        return {
            "keysets": [ # TODO: get all keysets and return them all
                {
                    "id": plugin.keysetId,
                    "unit": 'sat',
                    "active": True
                }
            ]
        }


@plugin.method("cashu-dev-get-privkeys")
def get_priv_keys(plugin: Plugin):
    return {key: value.secret.hex() for key, value in plugin.keys.items()}

def mint_quote_response(quote: str, rpc_invoice):
    return {
        "quote": quote,
        "request": rpc_invoice.get("bolt11"),
        "paid": False if rpc_invoice.get("status") == "unpaid" else True,
        "expiry": rpc_invoice.get("expires_at")
    }

# https://github.com/cashubtc/nuts/blob/main/04.md#mint-quote
@plugin.method("cashu-get-quote")
def mint_token(plugin: Plugin, amount, unit):
    quote = crypto.generate_quote()
    # TODO: check that amount and unit are valid
    invoice = plugin.rpc.invoice(
        amount_msat=amount * 1000, 
        label=f'cashu:{quote}', 
        description="An invoice"
    )
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#check-mint-quote-state
@plugin.method("cashu-check-quote")
def check_mint_status(plugin: Plugin, quote: str):
    invoice = plugin.rpc.listinvoices(label=f'cashu:{quote}').get("invoices")[0]
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#minting-tokens
@plugin.method("cashu-mint")
def mint_token(plugin: Plugin, quote: str, blinded_messages):
    invoice = plugin.rpc.listinvoices(label=f'cashu:{quote}').get("invoices")[0] # TODO: handle when invoices[0] DNE
    if invoice.get("status") == "unpaid":
        return {"error": "invoice not paid"}
    requested_amount = sum([int(b["amount"]) for b in blinded_messages])
    quote_amount = int(invoice.get("amount_msat")) / 1000
    if requested_amount != quote_amount:
        return {"error": "invalid amount"}
    blinded_sigs = []
    for b in blinded_messages:
        k = plugin.keys[int(b["amount"])]
        C_ = crypto.blind_sign(b["B_"], k)
        blinded_sigs.append({
            "amount": b["amount"],
            "id": plugin.keysetId,
            "C_": C_.format().hex()
        }) 
        # TODO: add quoteId to list of quotes for issued tokens 
    return blinded_sigs

# https://github.com/cashubtc/nuts/blob/main/05.md#melt-quote
@plugin.method("cashu-melt-quote")
def get_melt_quote(plugin: Plugin, req: str, unit: str): # QUESTION: why does 'request' not work but 'req' does?
    """Returns a quote for melting tokens"""
    amount = plugin.rpc.decodepay(req).get("amount_msat") // 1000
    response = {
        "quote": crypto.generate_quote(),
        "amount": amount,
        "fee_reserve": 0, # TODO: add fee reserve
        "paid": False,
        "expiry": 0 # TODO: add expiry... invoice expiry? 1 minute?
    }
    # add request to what we store so we can get the bolt11 later
    response_with_request = {**response, "request": req}
    plugin.melt_quotes[response["quote"]] = response_with_request
    return response


@plugin.method("cashu-check-melt-quote")
def check_melt_quote(plugin: Plugin, quote: str):
    """Checks the status of a melt quote request"""
    stored_quote = plugin.melt_quotes.get(quote)
    if not stored_quote:
        return {"error": "quote not found"}
    # if paid, then payment will be in the list of pays otherwise assume not paid
    try:
        payment = plugin.rpc.listpays(bolt11=stored_quote["request"]).get("pays")[0]
        paid = True if payment.get("status") == "complete" else False
    except:
        paid = False

    without_request = stored_quote.copy()
    without_request.pop("request")
    without_request["paid"] = paid
    return without_request

# BlindedMessage: https://github.com/cashubtc/nuts/blob/main/00.md#blindedmessage
@plugin.method("cashu-sign")# TODO: add id to specify which keyset to use
def sign(plugin, amount, B_):
    try:
        k = plugin.keys[int(amount)]
    except:
        return {"error":"unsupported amount"} # TODO: return a proper error
    C_ = crypto.blind_sign(B_, k)
    id = plugin.keysetId
    return {
        "amount": amount,
        "id": id,
        "C_": C_.format().hex()
    }

plugin.run()