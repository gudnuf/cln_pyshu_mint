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
    PostSwapResponse,
    MeltQuote
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

    mint_quote = mint.get_mint_quote(quote)

    return PostQuoteMintResponse(
        quote=mint_quote.quote_id,
        request=mint_quote.request,
        paid=mint_quote.paid,
        expiry=mint_quote.expiry
    )


@plugin.method("cashu-mint")
def mint_token(plugin: Plugin, quote: str, outputs):
    """
    Returns blinded signatures for blinded messages once a quote request is paid
    """
    # TODO: validate outputs list

    promises = mint.mint_tokens(outputs=outputs, quote_id=quote)

    return PostMintResponse(promises)


@plugin.method("cashu-quote-melt")
def get_melt_quote(plugin: Plugin, req: str, unit = 'sat', amount: int = None):
    """Returns a quote for melting tokens"""
    melt_quote = mint.melt_quote(bolt11=req, amount=amount)

    melt_quote.save()

    return PostQuoteMeltResponse(
        quote=melt_quote.quote_id,
        amount=melt_quote.amount_sat,
        fee_reserve=melt_quote.fee_reserve,
        paid=melt_quote.paid,
        expiry=melt_quote.expiry
    )


@plugin.method("cashu-check-melt")
def check_melt_quote(plugin: Plugin, quote: str):
    """Checks the status of a melt quote request"""

    melt_quote: MeltQuote = MeltQuote.find(quote_id=quote)

    paid = melt_quote.is_paid()
    melt_quote.paid = paid
    melt_quote.update()

    return PostQuoteMeltResponse(quote=quote,
                                 amount=melt_quote.amount_sat,
                                 fee_reserve=melt_quote.fee_reserve,
                                 paid=melt_quote.paid,
                                 expiry=melt_quote.expiry
                                 )


@plugin.method("cashu-melt")
def melt_token(plugin: Plugin, quote: str, inputs: list, outputs: list):
    """melt tokens"""

    quote = MeltQuote.find(quote_id=quote)

    paid, preimage = mint.melt_tokens(quote, inputs, outputs)

    return PostMeltResponse(paid=paid, preimage=preimage)


@plugin.method("cashu-swap")
def swap(plugin, inputs, outputs):
    """swap tokens for other tokens"""

    blinded_sigs = mint.swap_tokens(inputs, outputs)

    return PostSwapResponse(sigs=blinded_sigs)


@plugin.method("cashu-route-map")
def route_map(plugin):
    route_map = [
        {
            "path": "/keys",
            "cmd": "cashu-get-keys",
            "method": "GET"
        },
        {
            "path": "/keysets",
            "cmd": "cashu-get-keysets",
            "method": "GET"
        },
        {
            "path": "/keys/<keyset_id>",
            "cmd": "cashu-get-keys",
            "method": "GET"
        },
        {
            "path": "/mint/quote/bolt11",
            "cmd": "cashu-quote-mint",
            "method": "POST"
        },
        {
            "path": "/mint/quote/bolt11/<quote_id>",
            "cmd": "cashu-check-mint",
            "method": "GET"
        },
        {
            "path": "/mint/bolt11",
            "cmd": "cashu-mint",
            "method": "POST"
        },
        {
            "path": "/melt/quote/bolt11",
            "cmd": "cashu-quote-melt",
            "method": "POST",
            "param_overrides": {
                "request": "req"
            }
        },
        {
            "path": "/melt/quote/bolt11/<quote_id>",
            "cmd": "cashu-check-melt",
            "method": "GET"
        },
        {
            "path": "/melt/bolt11",
            "cmd": "cashu-melt",
            "method": "POST"
        },
        {
            "path": "/swap",
            "cmd": "cashu-swap",
            "method": "POST"
        }
    ]

    return route_map


plugin.run()
