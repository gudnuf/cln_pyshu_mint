#!/nix/store/5k91mg4qjylxbfvrv748smfh51ppjq0g-python3-3.11.6/bin/python

from pyln.client import Plugin
from utilities.KeySet import KeySet
from utilities import crypto
from utilities.utils import create_blinded_sigs, tokens_issued, mark_quote_issued, mark_token_spent, validate_inputs, find_invoice
from utilities.rpc_plugin import plugin

# TODO: handle returns... maybe just throw errors and then catch them all the same way
# rather than directly returning errors? Also is there a better way to return all the objects?
# what about like how I did with `mint_quote_response`

@plugin.init()
def init(options, configuration, plugin):
    """initialize the plugin"""
    seed = "johnny apple" # TODO: can we get the hsm secret from the node? Or make the node derive the seed
    plugin.keyset = KeySet(settings={
        "seed": seed,
        "MAX_ORDER": int(options['max_order'], 10),
        "derivation_path": options["path"]
        })

# https://github.com/cashubtc/nuts/blob/main/01.md#nut-01-mint-public-key-exchange
# GET /keys
@plugin.method("cashu-get-keys")
def get_keys(plugin: Plugin):
    """Returns the public keyset of the mint"""
    public_keys = plugin.keyset.public_keys
    return {
            "keysets": [
                {
                    "id": plugin.keyset.id,
                    "unit": 'sat',
                    "keys": {
                        key: value.format().hex() for key, value in public_keys.items()
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
                    "id": plugin.keyset.id,
                    "unit": 'sat',
                    "active": True
                }
            ]
        }


# TODO: make a way / figure out how to turn this off xD
@plugin.method("cashu-dev-get-privkeys")
def get_priv_keys(plugin: Plugin):
    """get mint's private keys"""
    return {key: value.secret.hex() for key, value in plugin.keyset.private_keys.items()}

# TODO: move this?? 
def mint_quote_response(quote: str, rpc_invoice):
    return {
        "quote": quote,
        "request": rpc_invoice.get("bolt11"),
        "paid": False if rpc_invoice.get("status") == "unpaid" else True,
        "expiry": rpc_invoice.get("expires_at")
    }

# https://github.com/cashubtc/nuts/blob/main/04.md#mint-quote
# POST /v1/mint/quote/bolt11
@plugin.method("cashu-quote-mint")
def mint_token(plugin: Plugin, amount, unit):
    """Returns a quote for minting tokens"""
    quote = crypto.generate_quote()
    invoice = plugin.rpc.invoice(
        amount_msat=amount * 1000, 
        label=f'cashu:{quote}', 
        description="An invoice" # TODO: come up with a better description
    )
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#check-mint-quote-state
# GET /v1/mint/quote/bolt11/{quote_id}
@plugin.method("cashu-check-mint")
def check_mint_status(plugin: Plugin, quote: str):
    """Checks the status of a quote request"""
    invoice = find_invoice(plugin, quote_id=quote)
    if invoice == None:
        return {"error": "invoice not found"}
    return mint_quote_response(quote, invoice)

# https://github.com/cashubtc/nuts/blob/main/04.md#minting-tokens
# POST /v1/mint/bolt11
@plugin.method("cashu-mint")
def mint_token(plugin: Plugin, quote: str, outputs):
    """Returns blinded signatures for blinded messages once a quote request is paid"""
    # check that we haven't already issued tokens 
    if tokens_issued(plugin, quote_id=quote):
        return {"error": "tokens already issued for this quote"}
    invoice = find_invoice(plugin, quote_id=quote)
    if invoice == None:
        return {"error": "invoice not found"}
    if invoice.get("status") == "unpaid":
        return {"error": "invoice not paid"}
    requested_amount = sum([int(b["amount"]) for b in outputs])
    quote_amount = int(invoice.get("amount_msat")) / 1000
    if requested_amount != quote_amount:
        return {"error": "invalid amount"}
    # make sure we do not give out tokens again
    mark_quote_issued(plugin, quote_id=quote)
    sigs = create_blinded_sigs(plugin, outputs)
    return {
        "signatures": sigs
    }

# https://github.com/cashubtc/nuts/blob/main/05.md#melt-quote
# POST /v1/melt/quote/bolt11
@plugin.method("cashu-quote-melt")
def get_melt_quote(plugin: Plugin, request: str, unit: str):
    """Returns a quote for melting tokens"""
    plugin.log(f"request: {request}")
    amount = plugin.rpc.decodepay(request).get("amount_msat") // 1000
    response = {
        "quote": crypto.generate_quote(),
        "amount": amount,
        "fee_reserve": 0, # TODO: add fee reserve
        "paid": False,
        "expiry": 0 # TODO: add expiry... invoice expiry? 1 minute?
    }
    # add request to what we store so we can get the bolt11 later
    response_with_request = {**response, "request": request}
    plugin.melt_quotes[response["quote"]] = response_with_request
    return response

# https://github.com/cashubtc/nuts/blob/main/05.md#check-melt-quote-state
# GET /v1/melt/quote/bolt11/{quote_id}
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

    without_request = stored_quote.copy() #TODO: how to do this better? don't write 3 lines of `without_request`
    without_request.pop("request")
    without_request["paid"] = paid
    return without_request

# https://github.com/cashubtc/nuts/blob/main/05.md#melting-tokens
# POST /v1/melt/bolt11
@plugin.method("cashu-melt")
def melt_token(plugin: Plugin, quote: str, inputs: list):
    """melt tokens"""
    quote = plugin.melt_quotes.get(quote)
    if not quote:
        return {"error": "quote not found"}
    bolt11 = quote["request"]
    # sum of all input amounts must equal the quote amount
    requested_amount = sum([int(i["amount"]) for i in inputs])
    quote_amount = int(quote["amount"])
    if requested_amount != quote_amount:
        return {"error": "invalid amount"}
    # validate the inputs and return an error message if present
    if (result := validate_inputs(plugin, inputs)) is not None:
        return result
    payment = plugin.rpc.pay(bolt11)
    ## store the secrets for each token so we know they've been spent
    [mark_token_spent(plugin, i["secret"]) for i in inputs]
    return {
        "paid": True if payment.get('status') == 'complete' else False,
        "preimage": payment.get('payment_preimage')
    }

# https://github.com/cashubtc/nuts/blob/main/03.md
# POST /v1/swap
@plugin.method("cashu-swap")
def swap(plugin, inputs, outputs):
    """swap tokens for other tokens"""
    plugin.log(f"inputs: {inputs}")
    plugin.log(f"outputs: {outputs}")
    inputs_sat = sum([int(proof["amount"]) for proof in inputs])
    outputs_sat = sum([int(b_["amount"]) for b_ in outputs])
    if inputs_sat is not outputs_sat:
        return {"error": "input amount does not match output amount"}
    # validate the inputs and return an error message if present
    if (result := validate_inputs(plugin, inputs)) is not None:
        return result
    blinded_sigs = create_blinded_sigs(plugin, outputs)
    ## store the secrets for each token so we know they've been spent
    [mark_token_spent(plugin, i["secret"]) for i in inputs]
    return blinded_sigs

plugin.run()