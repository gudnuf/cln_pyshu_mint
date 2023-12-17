#!/usr/bin/env python3

from pyln.client import Plugin

plugin = Plugin()

@plugin.init()  # Decorator to define a callback once the `init` method call has successfully completed
def init(options, configuration, plugin, **kwargs):
    plugin.log("Cashu mint plugin initialized")

plugin.run()