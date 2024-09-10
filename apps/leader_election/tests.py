from kazoo.client import KazooClient

from apps.leader_election.config import ALLOCATION_NODE, ELECTION_NODE

zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()

children = zk.get_children(ELECTION_NODE)

for child in children:
    zk.set(path=ALLOCATION_NODE + child, value=b"1,2")
