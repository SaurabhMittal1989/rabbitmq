import random
import time

from kazoo.client import KazooClient


def leader_callback():
    """Blocking call, until an input "y" is provided"""
    #Do the leader stuff"""
    ans = None
    while ans != "y":
        time.sleep(1)  # to let others join the leadership race
        print(election.contenders())
        ans = input('''I am the king now, Shall I abdicate the throne? (y/n)\n''')

    return


def do_follower_stuff():
    # poll to check if leader or follower
    # blocks, and if not leader, execute follower stuff
    # instead use locks to see if the leader stuff is done, and then can do follower stuff rather than waiting
    contenders = None
    while True:
        try:
            contenders = election.contenders()
        except:
            # retry in case election is not defined
            time.sleep(1)
        if contenders and contenders[0] == id:
            print(f"I {id} am the leader now!")
            break
        elif contenders:
            # Do the Follower stuff
            print(f"I {id} am the follower. {contenders}")
        time.sleep(5)  # Check every 5 seconds


zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()
zk.ensure_path("kingdom/election")
id = "node" + str(random.randint(1, 1000))

# Start the leader check in a non-blocking way, and execute follower code if leader check is false
import threading

leader_thread = threading.Thread(target=do_follower_stuff)
leader_thread.start()

while True:
    # election.run blocks the thread, until elected
    # Once elected, the thread becomes leader until the func=whoIsKing returns,
    # this thread surrenders the leadership, once the func=whoIsKing returns
    # rejoin the leadership race, after surrendering the leadership, perpetually

    election = zk.Election("/kingdom/election", id)
    election.run(func=leader_callback)
