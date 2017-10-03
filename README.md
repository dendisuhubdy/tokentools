# Token Tool
Scripts to talk to a geth node to scrape contract logs for token transfers.
The `tokens.json` is a ditionary that mapes a token to its contract address and the block that its creator transaction appeared in (from [etherscan.io](etherscan.io)).
Only need to change the address of the geth client in the `makeconn` function.

**Dependencies**: [ethjsonrpc](https://github.com/ConsenSys/ethjsonrpc), [pyethereum](https://github.com/ethereum/pyethereum)

## `readcontract.py`
Has a good command line interface.

```bash
$ python readcontract.py --help

usage: readcontract.py [-h] command

positional arguments:
  command     
              contract: get transactions for one contract
              
              contracts: input a json with 'token' : ('address', int(first_block)) for all tokens
              
              transfers: get all token transfer for a given contract
              
              transfersall: read a json file with all tokens desired with the form 'name' : (str(addr), int(first_block)

optional arguments:
  -h, --help  show this help message and exit

```

`tokens.json` is used with the transfersall command

For `transfers`:
```bash
$ python readcontract.py transfers --help
usage: readcontract.py [-h] [-f F] addr token

positional arguments:
  addr        address of erc20 to scrape
  token         name of token for output file

optional arguments:
  -h, --help  show this help message and exit
  -f F        block to start from (default: 1)
```
