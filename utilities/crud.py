from .rpc_plugin import plugin
from .utils import TOKEN_SECRET_KEY_BASE


def mark_token_spent(secret: str):
    """
    `lightning-cli datastore key=['cashu', 'secrets', $secret] string=""`
    """
    key = TOKEN_SECRET_KEY_BASE.copy()
    key.append(secret)
    plugin.rpc.datastore(key=key, string="")
