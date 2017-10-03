from ethjsonrpc import EthJsonRpc
from collections import defaultdict
import argparse, sys, json
from threading import Thread
from ethereum.utils import sha3
from multiprocessing import Pool, Process, Lock
from argparse import RawTextHelpFormatter
transfer = 'Transfer(address,address,uint256)'
approval = 'Approval(address,address,uint256)'
transfer = '0x%s' % sha3(transfer).encode('hex')
approval = '0x%s' % sha3(approval).encode('hex')

def ih(i):
    return int(i, 16)

def makeconn():
    return EthJsonRpc('172.17.0.26', 8545)

_mapping = {}
def getblockbyhash(h, c):
    if h in _mapping:
        return _mapping[h]
    else:
        _mapping[h] = c.eth_getBlockByHash(h)
        return _mapping[h]


def readcontracttxs(caddr, firstblock, ico):
    print "Looking for ico=%s with addr=%s"
    c = makeconn()
    relevant_txs = []
    amt_recv = 0
    amt_sent = 0
    with open('./contracts/%s.csv' % (ico), 'w') as f:
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
def getlogs(filt, c, ico):
    lock.acquire()
    print "Got lock for ico=%s" % ico
    logs = c.eth_getFilterLogs(filt)
    print 'Logs for ico=%s' % ico
    lock.release()
    return logs 
        
def readtransfers(caddr, ico, block=0):
    c = makeconn()
    newfilter = c.eth_newFilter(from_block=hex(block), to_block="latest", address=caddr, topics=[transfer])
    print 'For ico=%s, filter=%s' % (ico,newfilter)
    logs = getlogs(newfilter, c, ico)
    print "Looking in ico=%s for transfers" % ico
    with open('./transfers/%s.csv' % ico, 'w') as f:
        for log in logs:
            block = getblockbyhash(log['blockHash'], c)
            blockno = block['number']
            timestamp = block['timestamp']
            fro = '0x%s' % log['topics'][1][64-40+2:]
            to = '0x%s' % log['topics'][2][64-40+2:]
            amt = int(int(log['data'], 16) / 10**18)
            f.write('%s,%s,%s,%s,%d\n' % (ih(blockno), ih(timestamp), to, fro, amt))

def contracttxs():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', type=str, help="address of erc20 to scrape")
    parser.add_argument('ico', type=str, help="name of token for output file")
    parser.add_argument('-b', type=int, help="block number of creator transaction")
    args = parser.parse_args(sys.argv[2:])
    print args.b
    if args.b:
        readcontract(args.addr, args.b, args.ico)
    else:
        readcontract(args.addr, 0, args.ico)

def contractstxs():
    parser = argparse.ArgumentParser()
    parser.add_argument("icos", type=str, help="json file containing 'ico': ('address', int(first_block)) mappings")
    args = parser.parse_args(sys.argv[2:])
    addrmap = json.load(open(args.icos))
    threads = []
    for ico,(addr, block) in addrmap.iteritems():
        t = Thread(target=readcontract, args=(addr, block, ico))
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()

def transfers():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', type=str, help="address of erc20 to scrape")
    parser.add_argument('ico', type=str, help="name of token for output file")
    parser.add_argument('-f', type=int, default=1, help="block to start from (default: 1)")
    args = parser.parse_args(sys.argv[2:])
    if args.f:
        readtransfers(args.addr, args.ico, args.f)
    else:
        readtransfers(args.addr, args.ico) 



def transfersall():
    parser = argparse.ArgumentParser()
    parser.add_argument('icos', type=str, help="json of icos with 'name' : (int(addr), int(first_block))")
    args = parser.parse_args(sys.argv[2:])
    d = json.load(open(args.icos))
    for ico,(addr,block) in d.iteritems():
        Process(target=readtransfers, args=(addr, ico, block)).start()
             
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('command', type=str, help="\ncontract: get transactions for one contract\n\ncontracts: input a json with 'ico' : ('address', int(first_block)) for all icos\n\ntransfers: get all token transfer for a given contract\n\ntransfersall: read a json file with all icos desired with the form 'name' : (str(addr), int(first_block)")
    args = parser.parse_args(sys.argv[1:2])
    locals()[args.command]()


