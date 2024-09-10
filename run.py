import time

from apps.leader_election.leader_election import start, sequence

if __name__ == "__main__":
    start()
    time.sleep(20)
    print(f"Exited: {sequence}")