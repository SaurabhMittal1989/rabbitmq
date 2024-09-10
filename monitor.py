import time

from kazoo.client import KazooClient

zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()

ignore_list = ["/zookeeper"]
def _print_node_tree(path, tree):
    if zk.exists(path):

        data, stat = zk.get(path)
        line = f"ZNode: {path}, Data: {data.decode('utf-8')}, Version: {stat.version}"
        if path not in ignore_list:
            tree.append(line)
        else:
            return []

    else:
        print(f"Znode does not exist: {path}")
    for child in zk.get_children(path):
        _print_node_tree(f"{path}/{child}", tree=tree)

    return tree

def print_node_tree(path="", event="", i= ""):
    """Thread Safe Print"""
    tree = []
    tree=_print_node_tree(path, tree=tree)
    newline = "\n"
    print(f"----------{event}{i}----------------\n"
          f"{newline.join(tree)}{newline}"
          f"--------------------------")

if __name__ == "__main__":
    i=0
    while True:
        i = i + 1
        print_node_tree(i=i)

        time.sleep(15)