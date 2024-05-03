from pyln.client import Plugin
from . import crypto

# question: is there a way to make these functions work so that we do not have to pass the plugin to all of them??
# ... should this be a class? Or are they fine?

ISSUED_TOKEN_KEY_BASE = ["cashu", "issued_tokens"]
TOKEN_SECRET_KEY_BASE = ["cashu", "token_secrets"]
MELT_QUOTE_KEY_BASE = ["cashu", "melt_quotes"]


def find_mint_quote(plugin: Plugin, quote_id: str):
    """look for a mint quote ID in the datastore"""
    key = ISSUED_TOKEN_KEY_BASE.copy()
    key.append(quote_id)
    quote = plugin.rpc.listdatastore(key=key)['datastore']
    return quote


def tokens_issued(plugin: Plugin, quote_id: str):
    """check datastore for mint quote ID"""
    quote = find_mint_quote(plugin, quote_id)
    if quote == []:
        return False
    else:
        return True


def mark_quote_issued(plugin: Plugin, quote_id: str):
    """store quote ID in datastore"""
    key = ISSUED_TOKEN_KEY_BASE.copy()
    key.append(quote_id)
    plugin.rpc.datastore(key=key, string="")


def find_token_secret(plugin: Plugin, secret: str):
    """look for a spent token secret in datastore"""
    key = TOKEN_SECRET_KEY_BASE.copy()
    key.append(secret)
    secret = plugin.rpc.listdatastore(key=key)["datastore"]
    return secret


def token_spent(plugin: Plugin, secret: str):
    """check datastore for token secret"""
    secret = find_token_secret(plugin, secret)
    if secret == []:
        return False
    else:
        return True


def mark_token_spent(plugin: Plugin, secret: str):
    """store spent token secret in the datastore"""
    key = TOKEN_SECRET_KEY_BASE.copy()
    key.append(secret)
    plugin.rpc.datastore(key=key, string="")


def validate_inputs(plugin, inputs):
    """check sigs and that inputs haven't been spent"""
    for i in inputs:
        plugin.log(f"i: {i}")
        k = plugin.keyset.private_keys[int(i["amount"])]
        plugin.log(f"k: {k.to_hex()}")
        C = i["C"]
        secret_bytes = i["secret"].encode()
        plugin.log(f"secret_bytes: {secret_bytes}")
        plugin.log(f"C: {C}")
        if not crypto.verify_token(C, secret_bytes, k):
            return {"error": "invalid signature on an input"}
        if token_spent(plugin, secret=i["secret"]):
            return {"error": f'token with secret {i["secret"]} already spent'}
    return None


def find_invoice(plugin: Plugin, quote_id: str):
    """find invoice with label of `cashu:{quote_id}`"""
    invoices = plugin.rpc.listinvoices(
        label=f'cashu:{quote_id}').get("invoices")
    if invoices == []:
        raise ValueError("invoice not found")
    else:
        # there should only be one invoice with this label
        bolt11: str = invoices[0].get("bolt11")
        paid: bool = invoices[0].get("status") == "paid"
        expires_at = invoices[0].get("expires_at")
        amount_msat = invoices[0].get("amount_msat")
        return bolt11, paid, expires_at, amount_msat


def create_blinded_sigs(keyset, blinded_messages):
    """sign all the blinded messages"""
    blinded_sigs = []
    for b in blinded_messages:
        k = keyset.private_keys[int(b["amount"])]
        C_ = crypto.blind_sign(b["B_"], k)
        blinded_sigs.append({
            "amount": b["amount"],
            "id": keyset.id,
            "C_": C_.format().hex()
        })
    return blinded_sigs


def generate_invoice(plugin: Plugin, amount_msat, quote):
    """generate an invoice for a mint quote"""
    invoice = plugin.rpc.invoice(
        amount_msat=amount_msat,
        label=f'cashu:{quote}',
        description="Cashu mint request"
    )

    if invoice.get("bolt11") == None:
        raise ValueError("failed to generate invoice")
    else:
        return invoice.get("bolt11"), invoice.get("expires_at")


def sum_inputs(inputs):
    return sum([int(proof["amount"]) for proof in inputs])


def sum_outputs(outputs):
    return sum([int(b_["amount"]) for b_ in outputs])
