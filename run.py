import time

from apps.client_side_consumer_balancer.legacy.leader_election import start, sequence

if __name__ == "__main__":
    start()
    time.sleep(20)
    print(f"Exited: {sequence}")