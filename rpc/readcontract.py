from ethjsonrpc import EthJsonRpc
from collections import defaultdict
import argparse, sys, json
from threading import Thread
from ethereum.utils import sha3
from multiprocessing import Pool, Process, Lock
from argparse import RawTextHelpFormatter
import time

transfer = 'Transfer(address,address,uint256)'
approval = 'Approval(address,address,uint256)'
decimals = 'decimals()'
decimals = '0x%s' % sha3(decimals).encode('hex')[:32]
transfer = '0x%s' % sha3(transfer).encode('hex')
approval = '0x%s' % sha3(approval).encode('hex')

def ih(i):
    return int(i, 16)

def makeconn():
    return EthJsonRpc('172.19.0.17', 8545)

def blocknumberoracle():
    _mapping = {}    
    def r(h,c):
        if h in _mapping:
            return _mapping[h]
        else:
            _mapping[h] = c.eth_getBlockByHash(h)['number']
            return _mapping[h]
    return r

def readcontracttxs(caddr, firstblock, token):
    print "Looking for token=%s with addr=%s"
    c = makeconn()
    relevant_txs = []
    amt_recv = 0
    amt_sent = 0
    with open('./contracts/%s.csv' % (token), 'w') as f:
        try:
            currblock = firstblock
            while currblock != c.eth_blockNumber():
                block = c.eth_getBlockByNumber(currblock)
                txsinblock = []
                for tx in block['transactions']:
                    if tx['to'] is not None and ih(tx['to']) == ih(caddr):
                        txsinblock.append(tx)
                        print 'relevant tx'
                        f.write('%s,%s,%s,%s,%s,%s\n' % (currblock, block['timestamp'], tx['to'], tx['from'], tx['value'], caddr))
                        amt_recv += ih(tx['value'])
                    if tx['from'] is not None and ih(tx['from']) == ih(caddr):
                        f.write('%s,%s,%s,%s,%s,%s\n' % (currblock, block['timestamp'], tx['to'], tx['from'], tx['value'], caddr))
                        print 'relevant txs'
                        amr_sent += ih(tx['value'])
                relevant_txs += txsinblock
                if len(txsinblock) != 0:
                    print 'Txs relevant=%d in block=%d' % (len(txsinblock), currblock)
                currblock += 1
            print 'Done processing blocks. Contract=%s has total recv=%d, sent=%d' % (caddr, amt_recv, amt_sent)
        except KeyboardInterrupt:
            pass         

lock = Lock()
def getlogs(filt, c, token):
    lock.acquire()
    print "Got lock for token=%s" % token
    logs = c.eth_getFilterLogs(filt)
    print 'Logs for token=%s' % token
    lock.release()
    return logs 
  
def getdecimals(addr, c):
    num = c.eth_call(to_address=addr, data=decimals)
    if num == '0x':
        return 18
    else:
        return ih(num)

try:
    _blocktimestamps = pickle.load(open('blocktimestamp.dump'))
    print 'Opened blocktimestamps from pickle.'
except:
    print 'No pickle for blocktimestamps, initialize empty.'
    _blocktimestamps = {}

_blocknumbers = {}
def getblocknumberbyhash(h, c):
    if h in _blocknumbers:
        return _blocknumbers[h]
    else:
        block = c.eth_getBlockByHash(h)
        _blocknumbers[h] = block['number']
        _blocktimestamps[h] = block['timestamp']
        return _blocknumbers[h]
    
def getblocktimestampbyhash(h,c):
    if h in _blocktimestamps:
        return _blocktimestamps[h]
    else:
        block = c.eth_getBlockByHash(h)
        _blocknumbers[h] = block['number']
        _blocktimestamps[h] = block['timestamp']
        return _blocktimestamps[h]
 
def readtransfers(caddr, token, block=0):
    try:
        c = makeconn()
        newfilter = c.eth_newFilter(from_block=hex(block), to_block="latest", address=caddr, topics=[transfer])
        print 'For token=%s, filter=%s' % (token,newfilter)
        logs = getlogs(newfilter, c, token)
        print "Looking in token=%s for transfers" % token
        numdec = getdecimals(caddr, c)
        output = ''
        print len(logs)
        for log in logs:
            blockno = log['blockNumber']
            timestamp = getblocktimestampbyhash(log['blockHash'], c)
            fro = '0x%s' % log['topics'][1][64-40+2:]
            to = '0x%s' % log['topics'][2][64-40+2:]
            amt = int(int(log['data'], 16) / 10.0**numdec)
            output += '%s,%s,%s,%s,%d\n' % (ih(blockno), ih(timestamp), to, fro, amt)
            
        f = open('./transfers/%s.csv' % token, 'w')
        f.write(output)
        f.close()
    except: pass

    import pickle
    pickle.dump(_blocktimestamps, open('blocktimestamps.dump', 'w'))
          

def contracttxs():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', type=str, help="address of erc20 to scrape")
    parser.add_argument('token', type=str, help="name of token for output file")
    parser.add_argument('-b', type=int, help="block number of creator transaction")
    args = parser.parse_args(sys.argv[2:])
    print args.b
    if args.b:
        readcontract(args.addr, args.b, args.token)
    else:
        readcontract(args.addr, 0, args.token)

def contractstxs():
    parser = argparse.ArgumentParser()
    parser.add_argument("tokens", type=str, help="json file containing 'token': ('address', int(first_block)) mappings")
    args = parser.parse_args(sys.argv[2:])
    addrmap = json.load(open(args.tokens))
    threads = []
    for token,(addr, block) in addrmap.iteritems():
        t = Thread(target=readcontract, args=(addr, block, token))
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()

def transfers():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', type=str, help="address of erc20 to scrape")
    parser.add_argument('token', type=str, help="name of token for output file")
    parser.add_argument('-f', type=int, default=1, help="block to start from (default: 1)")
    args = parser.parse_args(sys.argv[2:])
    if args.f:
        readtransfers(args.addr, args.token, args.f)
    else:
        readtransfers(args.addr, args.token) 



def transfersall():
    parser = argparse.ArgumentParser()
    parser.add_argument('tokens', type=str, help="json of tokens with 'name' : (int(addr), int(first_block))")
    args = parser.parse_args(sys.argv[2:])
    d = json.load(open(args.tokens))
    for token,(addr,block) in d.iteritems():
        readtransfers(addr, token, block)
             
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('command', type=str, help="\ncontract: get transactions for one contract\n\ncontracts: input a json with 'token' : ('address', int(first_block)) for all tokens\n\ntransfers: get all token transfer for a given contract\n\ntransfersall: read a json file with all tokens desired with the form 'name' : (str(addr), int(first_block)")
    args = parser.parse_args(sys.argv[1:2])
    locals()[args.command]()


