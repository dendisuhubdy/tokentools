from ethjsonrpc import EthJsonRpc

c = EthJsonRpc('172.17.0.26', 8545)

print 'Net Version', c.net_version()
print 'web3 client version', c.web3_clientVersion()
print 'gas price', c.eth_gasPrice()
print 'block number', c.eth_blockNumber()
print 'eth syncing', c.eth_syncing()
