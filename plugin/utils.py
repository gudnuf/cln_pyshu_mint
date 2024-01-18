from pyln.client import Plugin

ISSUED_TOKEN_KEY_BASE = ["cashu", "issued_tokens"]

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
