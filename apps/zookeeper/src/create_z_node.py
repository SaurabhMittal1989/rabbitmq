import time
import traceback

from apps.zookeeper.src.zk_client import zk, create_zk_client


def watcher(event):
    # check to see what the children are now
    print("event: ", event)
    children = zk.get_children("/cloudxlab/", watch=watcher)
    print(children)


# create a znode in Zookeeper
def create_node(path, *args, **kwargs) -> bool:
    """Returns True if Success"""
    try:
        zk.create("path", args, kwargs)
        return True
    except Exception as e:
        print(f"failed to craete Zoo Keeper Node: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":

    # Call my_func when the children change
    create_zk_client()
    children = zk.get_children("/cloudxlab/", watch=watcher)
    print(children)

    children = zk.create("/cloudxlab/a", ephemeral=True) if not zk.exists("/cloudxlab/a") else None
    children = zk.create("/cloudxlab/b", ephemeral=True) if not zk.exists("/cloudxlab/b") else None

    zk.stop()
    time.sleep(5)
    zk.start()

    time.sleep(100)
