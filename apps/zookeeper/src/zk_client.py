from kazoo.client import KazooClient

zk = None


def create_zk_client():
    global zk
    if not zk:
        zk = KazooClient(hosts='127.0.0.1:2181')
        zk.start()
        zk.add_listener(connection_listener)
    else:
        return zk


def connection_listener(state):
    if state == "DISCONNECTED":
        print("Client is disconnected from ZooKeeper")
    elif state == "CONNECTED":
        print("Client is connected to ZooKeeper")
    elif state == "LOST":
        print("Client lost connection to ZooKeeper")
