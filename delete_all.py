import time

from kazoo.client import KazooClient

zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()


if __name__ == "__main__":
    for node in zk.get_children("/"):
        try:
            zk.delete(node, recursive=True)
            print(f"Recursive delete {node}")
        except Exception as e:
            print(e)