#!/usr/bin/env python3

from typing import Dict
from coincurve import PublicKey
from pyln.client import Plugin
import keys

plugin = Plugin()

plugin.keys: keys.PrivKeyset
plugin.keysetId = ""

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

plugin.run()