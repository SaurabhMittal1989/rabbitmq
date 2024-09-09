from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError, ZookeeperError
from kazoo.protocol.states import KazooState

def connection_listener(state: KazooState):
        print(f"Client is {state} from ZooKeeper")


class ZooKeeper:
    zk =None
    @staticmethod
    def __init__():
        if not ZooKeeper.zk:
            ZooKeeper.zk = KazooClient(hosts='127.0.0.1:2181')
            ZooKeeper.zk.start()
            ZooKeeper.zk.add_listener(connection_listener)

    def watcher(self, event):
        # check to see what the children are now
        self.print_node_tree(path="", event=event)

    def create_node(self, path, *args, **kwargs) -> str:
        """Create a Znode in Zookeeper
        Returns path if Success"""
        try:
            path = self.zk.create(path, *args, **kwargs)
            return path
        except NodeExistsError as e:
            print(f"failed to create Zoo Keeper Node: {path}. Exception {e.__repr__()}")
            # traceback.print_exc()

    def delete_node(self, path, *args, **kwargs) -> bool:
        """Delete a znode in Zookeeper
        Returns True if Success"""
        try:
            self.zk.delete(path, *args, **kwargs)
            return True
        except ZookeeperError as e:
            print(f"failed to delete ZNode: {e}")
            # traceback.print_exc()
            return False

    def print_node_tree(self, path="", event=""):
        """Thread Safe Print"""
        tree = []
        self._print_node_tree(path, tree=tree)
        newline = "\n"
        print(f"----------{event}----------------\n"
              f"{newline.join(tree)}{newline}"
              f"--------------------------")

    def _print_node_tree(self, path, tree):
        if self.zk.exists(path):
            data, stat = self.zk.get(path)
            line = f"ZNode: {path}, Data: {data.decode('utf-8')}, Version: {stat.version}"
            tree.append(line)
        else:
            print(f"Znode does not exist: {path}")
        for child in self.zk.get_children(path):
            self._print_node_tree(f"{path}/{child}", tree=tree)





