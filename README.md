# CLN Cashu Mint Plugin

A plugin for running a mint right on your node!

Currently, still in development...

## Running the dev environemnt

### Get Nix

This project is nixified, so first make sure you have [nix installed](https://nixos.org/download) and [experimental features](https://nixos.wiki/wiki/Nix_command) turned on so that you can use the `nix develop` command.

Once nix is installed, clone the repo and inside the project directory run:

```
nix develop
```

The first time you run this expect to wait for everthing to download/build.

Now you have bitcoin and lightning nodes, all the required packages, and shell variables defined!

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

```
fund_nodes
```

### Start the plugin

The [`restart_plugin.sh`](./restart_plugin.sh) script takes an optional argument to specify which node you want to start the plugin on.

```
./restart_plugin.sh 1 #start the plugin on node 1
```

**NOTE**: any changes to your plugin will require you to re run this script.

## Jupyter notebooks

Right now, there is a lot of scratch in the notebooks. The [swap.ipynb](./jupyter_notebooks/swap.ipynb) and [mint_melt.ipynb](./jupyter_notebooks/mint_melt.ipynb) are pretty cleaned up and serve as the current docs for the plugin.

