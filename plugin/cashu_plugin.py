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
@plugin.method("cashu-quote-mint")
def mint_token(plugin: Plugin, amount, unit):
    """Returns a quote for minting tokens"""
    quote = crypto.generate_quote()
    # TODO: check that amount and unit are valid
    invoice = plugin.rpc.invoice(
        amount_msat=amount * 1000, 
        label=f'cashu:{quote}', 
        description="An invoice"
    )
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#check-mint-quote-state
@plugin.method("cashu-check-mint")
def check_mint_status(plugin: Plugin, quote: str):
    """Checks the status of a quote request"""
    invoice = plugin.rpc.listinvoices(label=f'cashu:{quote}').get("invoices")[0]
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#minting-tokens
@plugin.method("cashu-mint")
def mint_token(plugin: Plugin, quote: str, blinded_messages):
    """Returns blinded signatures for blinded messages once a quote request is paid"""
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
@plugin.method("cashu-quote-melt")
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


@plugin.method("cashu-check-melt")
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

def validate_inputs(plugin, inputs):
    all_valid = True
    for i in inputs:
        k = plugin.keys[int(i["amount"])]
        C = i["C"]
        secret_bytes = i["secret"].encode()
        if not crypto.verify_token(C, secret_bytes, k):
            all_valid = False
    return all_valid

@plugin.method("cashu-melt")
def melt_token(plugin: Plugin, quote: str, inputs: list):
    quote = plugin.melt_quotes.get(quote)
    if not quote:
        return {"error": "quote not found"}
    bolt11 = quote["request"]
    # sum of all input amounts must equal the quote amount
    requested_amount = sum([int(i["amount"]) for i in inputs])
    quote_amount = int(quote["amount"])
    if requested_amount != quote_amount:
        return {"error": "invalid amount"}
    if not validate_inputs(plugin, inputs):
        return {"error": "invalid inputs"}
    payment = plugin.rpc.pay(bolt11)
    return {
        "paid": True if payment.get('status') == 'complete' else False,
        "preimage": payment.get('payment_preimage')
    }

@plugin.method("cashu-swap")
def swap(plugin, inputs, outputs):
    inputs_sat = sum([int(proof["amount"]) for proof in inputs])
    outputs_sat = sum([int(b_["amount"]) for b_ in outputs])
    if inputs_sat is not outputs_sat:
        return {"error": "input amount does not match output amount"}
    if not validate_inputs(plugin, inputs):
        return {"error": "invalid inputs"}
    blinded_sigs = []
    for b in outputs:
        k = plugin.keys[int(b["amount"])]
        C_ = crypto.blind_sign(b["B_"], k)
        blinded_sigs.append({
            "amount": b["amount"],
            "id": plugin.keysetId,
            "C_": C_.format().hex()
        }) 
    return blinded_sigs
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