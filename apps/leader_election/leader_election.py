import random
import threading
import time

from kazoo.client import KazooClient
from kazoo.protocol.states import KazooState
from kazoo.recipe.watchers import DataWatch

from apps.leader_election.config import INSTANCE_ID_MAX, ELECTION_NODE, STOP_FLAG, ALLOCATION_NODE
from apps.leader_election.consumer import stop_consumer, start_consumer


def connection_listener(state: KazooState):
    global sequence
    print(f"Client is {state} from ZooKeeper: {sequence}")
    if state.CONNECTED:
        re_register()


def re_register():
    global sequence
    print(f"REREGISTER?: {sequence}")
    # check if already registered etc
    pass


zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()
zk.add_listener(connection_listener)

instance_id = random.randint(1, INSTANCE_ID_MAX)

sequence = None


def start():
    sequence_id = register_me()
    global sequence
    sequence = sequence_id
    if check_if_current_node_is_leader(sequence_id=sequence_id):
        leader_callback()

    @zk.DataWatch(STOP_FLAG)
    def update_consumer(*args, **kwargs):
        value = args[0]
        print(f"STOP Flag set to {value}")
        if value == b'1':
            stop_consumer()

        elif value == b'0':
            go = True
            while go:
                try:
                    global sequence
                    byte_queues, stat_queues = zk.get(path=ALLOCATION_NODE + sequence)
                    go = False
                    print(f"Got {ALLOCATION_NODE + sequence}: {byte_queues}")
                    queue_list = byte_queues.decode("utf-8").split(",")
                    start_consumer(queue_names=queue_list)

                except Exception as e:
                    print(f"Exception getting {ALLOCATION_NODE}: {e}")

                time.sleep(5)




def register_me() -> str:
    if not zk.exists(path=ELECTION_NODE):
        node = zk.create(path=ELECTION_NODE)
        print(f"created {node}")

    if not zk.exists(path=ALLOCATION_NODE):
        node = zk.create(path=ALLOCATION_NODE)
        print(f"created {node}")

    if not zk.exists(path=STOP_FLAG):
        node = zk.create(path=STOP_FLAG, value=b"1")
        print(f"created {node}")

    node = zk.create(path=ELECTION_NODE, sequence=True, value=bytes(f"{instance_id}", encoding="utf-8"), ephemeral=True)
    print(f"created {node}")

    sequence_id = node.split("/")[-1]

    return sequence_id


def check_if_current_node_is_leader(sequence_id) -> bool:
    all_instances = zk.get_children(path=ELECTION_NODE, include_data=False)
    if sorted(all_instances)[0] == sequence_id:
        return True
    else:
        set_watch_on_prev_seq(sequence_id=sequence_id)
        return False


def set_watch_on_prev_seq(sequence_id):
    all_instances: list = sorted(zk.get_children(path=ELECTION_NODE, include_data=False))
    index = all_instances.index(sequence_id)
    global sequence
    if index == 0:

        raise Exception(f"I am the leader {sequence}")
    else:
        index -= 1
    prev_seq_id = all_instances[index]
    done = zk.exists(path=ELECTION_NODE + prev_seq_id, watch=leader_callback)
    if not done:
        print(f"Prev Seq Id {prev_seq_id} does not exists: {sequence}")


def get_total_queues(mq_client):
    return range(20)


def get_consumer_queue_distribution(consumers, queues) -> dict:
    quota = int(len(queues) / len(consumers))+1
    i = 0
    assignment_dict = {}
    for consumer in consumers:
        j = i + quota if i + quota <= len(queues) else len(queues)
        assignment_dict[consumer] = queues[i:j]
        i = j

    print(assignment_dict)
    return assignment_dict


def stop_all_consumers():
    """Set a stop consumer flag. Consumers watch a flag"""
    zk.set(path=STOP_FLAG, value=b"1")

    # wait to check if all consumers are stopped
    all_consumers_stopped = False
    while not all_consumers_stopped:
        time.sleep(5)
        all_consumers_stopped = True


def start_all_consumers(allocations: dict):
    """Set the start consumer flag. Consumers watch a flag
    transactional update of config in zookeeper
    1. Delete previous configuration
    2. Update the new configuration
    3. Ask all consumers to start"""
    tr = zk.transaction()

    # publish the config to Zookeeper
    for children in zk.get_children(path=ALLOCATION_NODE):
        tr.delete(path=ALLOCATION_NODE + children)

    for consumer, queues in allocations.items():
        byte_data = bytes(",".join([str(q) for q in queues]), encoding="utf-8")
        tr.create(ALLOCATION_NODE + consumer, value=byte_data)
    tr.set_data(path=STOP_FLAG, value=b"0")
    tr.commit()


def wait_for_all_nodes_join():
    time.sleep(5)

def leader_callback(data=None):
    global sequence
    print(f"I became the leader {sequence}")
    wait_for_all_nodes_join()

    consumers = zk.get_children(path=ELECTION_NODE, watch=update_membership)
    queues = get_total_queues(mq_client=None)
    allocations = get_consumer_queue_distribution(consumers, queues)
    stop_all_consumers()

    start_all_consumers(allocations=allocations)
    print(f"All consumers restart command issued: {sequence}")



def update_membership(data):
    print(f"Redistributing Queues : {data}")
    leader_callback(data)




if __name__ == "__main__":
    start()

    print(f"Exited: {sequence}")
