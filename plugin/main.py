#!/usr/bin/env python3
from flask import Flask
from pyln.client import Plugin
import threading

class Main:
    def __init__(self):
        # Initialize Flask
        self.app = Flask(__name__)

        # Initialize Plugin
        self.plugin = Plugin()

        # Set up the plugin init callback
        @self.plugin.init()
        def init(options, configuration, plugin, **kwargs):
            plugin.log("Cashu mint plugin initialized")

        # Define Flask routes
        @self.app.route('/')
        def home():
            return "Cashu Mint Service"

    def start_plugin(self):
        # Run the plugin
        self.plugin.run()

    def start_flask(self):
        # Run the Flask app
        self.app.run(debug=True, use_reloader=False)

    def run(self):
        # Create threads for Flask and the plugin
        flask_thread = threading.Thread(target=self.start_flask)
        plugin_thread = threading.Thread(target=self.start_plugin)

        # Start threads
        flask_thread.start()
        plugin_thread.start()

        # Wait for threads to complete
        flask_thread.join()
        plugin_thread.join()

if __name__ == "__main__":
    main = Main()
    main.run()
