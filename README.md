# CLN Cashu Mint Plugin

A plugin for running a mint right on your node!

⚠️⚠️Currently, still in development⚠️⚠️

## Running the dev environemnt

### Get Nix

This project is nixified, so first make sure you have [nix installed](https://nixos.org/download) and [experimental features](https://nixos.wiki/wiki/Nix_command) turned on so that you can use the `nix develop` command.

Once nix is installed, clone the repo and inside the project directory run:

```
nix develop
```

The first time you run this expect to wait for everthing to download/build.

Now, you have **bitcoin and lightning nodes**, all the **required packages**, and **shell variables** defined!

### Start, fund, and connect your nodes

#### Start nodes in regtest

Source the [`startup_regtest.sh`](./startup_regtest.sh) script and then start 2 nodes.

```
source ./startup_regtest.sh
```

```
start_ln #default is 2 nodes
```

#### Fund and connect nodes

The `fund_nodes` function comes from the startup script and requires that all your nodes are running.

This function first checks to make sure your bitcoind wallet is funded, then sends coins to your lightning nodes, and finally opens a channel from node 1 to node 2.

```
fund_nodes
```

### Start the plugin

The [`restart_plugin.sh`](./restart_plugin.sh) script takes an _optional argument_ to specify which node you want to start the plugin on.

```
./restart_plugin.sh 1 #start the plugin on node 1
```

**NOTE**: any changes to your plugin will require you to re run this script.

## Jupyter notebooks

Right now, there is a lot of scratch in the notebooks. Check out the [mint_melt.ipynb](./jupyter_notebooks/mint_melt.ipynb) and [swap.ipynb](./jupyter_notebooks/swap.ipynb) notebooks to see a the flow of minting, melting, and swapping tokens.

Assuming you got the environment set up right _with nix_ these two notebooks should run all the way through!

>> Sometimes the node directories ends up in a bad state and things break... use the `stop_ln` then `destroy_ln` functions from `startup_regtest.sh` (or delete your node directories) to reset.

## RPC Commands

The RPC commands exposed by this plugin match each of the routes defined in the [cashu spec](https://github.com/cashubtc/nuts).

**For now, refer to the above notebooks on how to use these commands.**

Below is the summary of each method defined in the provided code, formatted in markdown as requested:

### cashu-get-keys
[spec](https://github.com/cashubtc/nuts/blob/main/01.md#nut-01-mint-public-key-exchange)
- **Route**: `GET /keys`
- **Summary**: Returns the public keyset of the mint.

### cashu-get-keysets
[spec](https://github.com/cashubtc/nuts/blob/main/02.md#multiple-keysets)
- **Routes**: `GET /keysets` & `GET /keyset/{keysetId}`
- **Summary**: Returns all or a specific keyset of the mint. Currently, it only supports returning the mint's primary keyset.

### cashu-dev-get-privkeys
- **Summary**: Retrieves the mint's private keys. This method exposes the private keys from the mint's keyset, formatted for external use. This method is development use only.

### cashu-quote-mint
[spec](https://github.com/cashubtc/nuts/blob/main/04.md#mint-quote)
- **Route**: `POST /v1/mint/quote/bolt11`
- **Summary**: Returns a quote for minting tokens. It generates a quote, and creates an invoice for the requested amount.

### cashu-check-mint
[spec](https://github.com/cashubtc/nuts/blob/main/04.md#check-mint-quote-state)
- **Route**: `GET /v1/mint/quote/bolt11/{quote_id}`
- **Summary**: Checks the status of a quote request for minting tokens. It finds the invoice associated with the quote and returns the quote's status, including whether it has been paid.

### cashu-mint
[spec](https://github.com/cashubtc/nuts/blob/main/04.md#minting-tokens)
- **Route**: `POST /v1/mint/bolt11`
- **Summary**: Returns blinded signatures for blinded messages once a quote request is paid. It verifies the quote's payment status, validates the requested amount, and issues blinded signatures if the conditions are met.

### cashu-quote-melt
[spec](https://github.com/cashubtc/nuts/blob/main/05.md#melt-quote)
- **Route**: `POST /v1/melt/quote/bolt11`
- **Summary**: Returns a quote for melting tokens.

### cashu-check-melt
[spec](https://github.com/cashubtc/nuts/blob/main/05.md#check-melt-quote-state)
- **Route**: `GET /v1/melt/quote/bolt11/{quote_id}`
- **Summary**: Checks the status of the invoice associated with the melt quote.

### cashu-melt
[spec](https://github.com/cashubtc/nuts/blob/main/05.md#melting-tokens)
- **Route**: `POST /v1/melt/bolt11`
- **Summary**: Processes melting tokens into a payment. It verifies the quote and the sum of input amounts, validates the inputs, and executes a payment if all conditions are met, marking tokens as spent.

### cashu-swap
[spec](https://github.com/cashubtc/nuts/blob/main/03.md)
- **Route**: `POST /v1/swap`
- **Summary**: Swaps tokens for other tokens. It validates the total amounts of inputs and outputs are equal, checks the inputs, creates blinded signatures for the outputs, and marks the input tokens as spent.
