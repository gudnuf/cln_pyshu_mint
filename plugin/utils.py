from pyln.client import Plugin

ISSUED_TOKEN_KEY_BASE = ["cashu", "issued_tokens"]
TOKEN_SECRET_KEY_BASE = ["cashu", "token_secrets"]

# look in node's datastore for an entry matching the quote_id
def find_mint_quote(plugin: Plugin, quote_id: str):
    key = ISSUED_TOKEN_KEY_BASE.copy()
    key.append(quote_id)
    quote = plugin.rpc.listdatastore(key=key)['datastore']
    return quote

# check if tokens have been issued for a quote id or not
def tokens_issued(plugin: Plugin, quote_id: str):
    quote = find_mint_quote(plugin, quote_id)
    if quote == []:
        return False
    else:
        return True
    
def mark_quote_issued(plugin: Plugin, quote_id: str):
    key = ISSUED_TOKEN_KEY_BASE.copy()
    key.append(quote_id)
    plugin.rpc.datastore(key=key, string="")

def find_token_secret(plugin: Plugin, secret: str):
    key = TOKEN_SECRET_KEY_BASE.copy()
    key.append(secret)
    secret = plugin.rpc.listdatastore(key=key)["datastore"]
    return secret

def token_spent(plugin: Plugin, secret: str):
    secret = find_token_secret(plugin, secret)
    if secret == []:
        return False
    else:
        return True
    
def mark_token_spent(plugin: Plugin, secret: str):
    key = TOKEN_SECRET_KEY_BASE.copy()
    key.append(secret)
    plugin.rpc.datastore(key=key, string="")

def validate_inputs(plugin, inputs):
    for i in inputs:
        k = plugin.keyset.private_keys[int(i["amount"])]
        C = i["C"]
        secret_bytes = i["secret"].encode()
        if not crypto.verify_token(C, secret_bytes, k):
            return {"error": "invalid signature on an input"}
        if token_spent(plugin, secret=i["secret"]):
            return {"error": f'token with secret {i["secret"]} already spent'}
    return None

