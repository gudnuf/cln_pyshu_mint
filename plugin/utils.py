from pyln.client import Plugin
import crypto

# question: is there a way to make these functions work so that we do not have to pass the plugin to all of them??
#... should this be a class? Or are they fine?

ISSUED_TOKEN_KEY_BASE = ["cashu", "issued_tokens"]
TOKEN_SECRET_KEY_BASE = ["cashu", "token_secrets"]

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
        k = plugin.keyset.private_keys[int(i["amount"])]
        C = i["C"]
        secret_bytes = i["secret"].encode()
        if not crypto.verify_token(C, secret_bytes, k):
            return {"error": "invalid signature on an input"}
        if token_spent(plugin, secret=i["secret"]):
            return {"error": f'token with secret {i["secret"]} already spent'}
    return None

def find_invoice(plugin: Plugin, quote_id:str):
    """find invoice with label of `cashu:{quote_id}`"""
    invoices = plugin.rpc.listinvoices(label=f'cashu:{quote_id}').get("invoices")
    if invoices == []:
        return None
    else:
        # there should only be one invoice with this label
        return invoices[0]
    
def create_blinded_sigs(plugin: Plugin, blinded_messages):
    """sign all the blinded messages"""
    blinded_sigs = []
    for b in blinded_messages:
        k = plugin.keyset.private_keys[int(b["amount"])]
        C_ = crypto.blind_sign(b["B_"], k)
        blinded_sigs.append({
            "amount": b["amount"],
            "id": plugin.keyset.id,
            "C_": C_.format().hex()
        }) 
    return blinded_sigs
