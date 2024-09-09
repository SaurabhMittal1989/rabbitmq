import time
from kazoo.recipe.watchers import ChildrenWatch

from apps.zookeeper.src.zk_client import ZooKeeper

if __name__ == "__main__":
    # Call my_func when the children change

    zk = ZooKeeper()
    zk.delete_node("/cloudxlab/", recursive=True)

    zk.print_node_tree("", "START")

    zk.create_node("/cloudxlab")
    ChildrenWatch(client=zk.zk,path="/cloudxlab", func=zk.watcher)
    zk.create_node("/cloudxlab/a")
    time.sleep(1)
    zk.create_node("/cloudxlab/b")

    zk.create_node("/cloudxlab/b/1", ephemeral=True)
    zk.create_node("/cloudxlab/b/2", ephemeral=True)
    zk.create_node("/cloudxlab/a/1", ephemeral=True)
    zk.create_node("/cloudxlab/a/2", ephemeral=True)

    zk.create_node("/cloudxlab/c", sequence = True, value=b"1",ephemeral=True)
    zk.create_node("/cloudxlab/c", sequence=True, value=b"2",ephemeral=True)
    zk.create_node("/cloudxlab/c", sequence=True, value=b"3",ephemeral=True)
    zk.create_node("/cloudxlab/c", sequence=True, value=b"4",ephemeral=True)

    # Start a transaction
    transaction = zk.zk.transaction()

    # Add multiple create operations to the transaction
    transaction.create('/node1', b'data1')
    transaction.create('/node2', b'data2')
    transaction.create('/node3', b'data3')

    # Commit the transaction
    results = transaction.commit()

    # Check the results
    for result in results:
        print(result)


    zk.print_node_tree("", "END")
    time.sleep(5)
    zk.zk.stop()
    time.sleep(5)
    zk.zk.start()
    time.sleep(5)
    zk.print_node_tree("", "AFTER RECONNECT")
    time.sleep(100)
