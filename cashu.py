#!/nix/store/5k91mg4qjylxbfvrv748smfh51ppjq0g-python3-3.11.6/bin/python

from pyln.client import Plugin
from utilities.models import (
    Mint,
    GetKeysResponse,
    GetKeysetsResponse,
    PostQuoteMintResponse,
    PostMintResponse,
    PostQuoteMeltResponse,
    PostMeltResponse,
    PostSwapResponse
)
from utilities.utils import (create_blinded_sigs,
                             tokens_issued,
                             mark_quote_issued,
                             mark_token_spent,
                             validate_inputs,
                             find_invoice
                             )
from utilities import crypto
from utilities.rpc_plugin import plugin

# TODO: handle returns... maybe just throw errors and then catch them all the same way rather than directly returning errors?


mint: Mint = None


@plugin.init()
def init(options, configuration, plugin):
    """initialize the plugin"""

    # TODO: can we use the hsm secret from the node? Or make the node derive the seed
    seed = "johnny apple"

    max_order = int(options['max_order'], 10)
    derivation_path = options["path"]

    global mint
    mint = Mint(derivation_path, seed, max_order)

    plugin.melt_quotes = {}

    plugin.log(f"plugin initialized.")

# TODO: add getinfo method


@plugin.method("cashu-get-keys")
def get_keys():
    """Returns the active public keyset of the mint"""

    return GetKeysResponse(keyset=mint.keyset)


@plugin.method("cashu-get-keysets")
def get_keysets(plugin: Plugin, keyset_id=None):
    """Returns all keysets of the mint or a specific keyset if requested"""

    if (keyset_id):
        keyset = mint.keyset if keyset_id == mint.keyset.id else None
        return GetKeysResponse(keyset=keyset)
    else:
        return GetKeysetsResponse(keysets=[mint.keyset])


# TODO: make a way / figure out how to turn this off xD
@plugin.method("cashu-dev-get-privkeys")
def get_priv_keys(plugin: Plugin):
    """get mint's private keys"""

    return {key: value.secret.hex() for key, value in plugin.keyset.private_keys.items()}


@plugin.method("cashu-quote-mint")
def get_mint_quote(plugin: Plugin, amount, unit):
    """Returns a quote for minting tokens"""
    quote = mint.mint_quote(amount_sat=int(amount))

    return PostQuoteMintResponse(
        quote=quote.quote_id,
        request=quote.request,
        paid=quote.paid,
        expiry=quote.expiry
    )


@plugin.method("cashu-check-mint")
def check_mint_status(plugin: Plugin, quote: str):
    """Checks the status of a quote request"""

    bolt11, paid, expires_at, _ = find_invoice(plugin, quote_id=quote)

    return PostQuoteMintResponse(quote, request=bolt11, paid=paid, expiry=expires_at)


@plugin.method("cashu-mint")
def mint_token(plugin: Plugin, quote: str, outputs):
    """
    Returns blinded signatures for blinded messages once a quote request is paid
    """

    if tokens_issued(plugin, quote_id=quote):
        return {"error": "tokens already issued for this quote"}

    _, paid, _, amount_msat = find_invoice(plugin, quote_id=quote)

    if not paid:
        return {"error": "invoice not paid"}

    requested_amount = sum([int(b["amount"]) for b in outputs])
    quote_amount = int(amount_msat) / 1000

    if requested_amount != quote_amount:
        return {"error": "invalid amount"}

    sigs = create_blinded_sigs(mint.keyset, outputs)

    mark_quote_issued(plugin, quote_id=quote)
    return PostMintResponse(sigs)


@plugin.method("cashu-quote-melt")
def get_melt_quote(plugin: Plugin, req: str, unit: str):
    """Returns a quote for melting tokens"""

    plugin.log(f"request: {req}")
    amount = plugin.rpc.decodepay(req).get("amount_msat") // 1000
    quote = crypto.generate_quote()
    response = PostQuoteMeltResponse(
        quote, amount, fee_reserve=0, paid=False).to_json()
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
        payment = plugin.rpc.listpays(
            bolt11=stored_quote["request"]).get("pays")[0]
        paid = True if payment.get("status") == "complete" else False
    except:
        paid = False

    # TODO: how to do this better? don't write 3 lines of `without_request`
    without_request = stored_quote.copy()
    without_request.pop("request")
    without_request["paid"] = paid
    return PostQuoteMeltResponse(quote=quote,
                                 amount=without_request["amount"], fee_reserve=without_request["fee_reserve"], paid=without_request["paid"], expiry=without_request.get("expiry"))


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

    if payment.get('status') == 'complete':
        [mark_token_spent(plugin, i["secret"]) for i in inputs]

        return PostMeltResponse(paid=True, preimage=payment.get('payment_preimage'))
    else:
        return PostMeltResponse(paid=False)


@plugin.method("cashu-swap")
def swap(plugin, inputs, outputs):
    """swap tokens for other tokens"""

    inputs_sat = sum([int(proof["amount"]) for proof in inputs])
    outputs_sat = sum([int(b_["amount"]) for b_ in outputs])

    if inputs_sat is not outputs_sat:
        return {"error": "input amount does not match output amount"}

    # validate the inputs and return an error message if present
    if (result := validate_inputs(plugin, inputs)) is not None:
        return result

    blinded_sigs = create_blinded_sigs(plugin, outputs)

    # store the secrets for each token so we know they've been spent
    [mark_token_spent(plugin, i["secret"]) for i in inputs]

    return PostSwapResponse(sigs=blinded_sigs)


plugin.run()
