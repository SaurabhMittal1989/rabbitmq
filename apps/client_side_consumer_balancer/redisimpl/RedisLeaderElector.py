import signal
import threading
import time
import uuid
from typing import Callable

import redis

from apps.client_side_consumer_balancer.LeaderElector import ILeaderElector
from apps.client_side_consumer_balancer.config import *
from apps.client_side_consumer_balancer.logger_config import *


class RedisLeaderElector(ILeaderElector):
    def __init__(self, redis_client, lock_key, node_id, lease_duration_ms, renewal_interval_s,
                 leader_callback: Callable):
        self.r = redis_client
        self.lock_key = lock_key
        self.node_id = node_id  # Unique ID for this instance
        self.lease_duration_ms = lease_duration_ms
        self.renewal_interval_s = renewal_interval_s
        self.leader_callback = leader_callback

        self._is_leader = False
        self._renewal_thread = None
        self._stop_event = threading.Event()

        # Load Lua scripts
        self._renew_script_sha = self.r.script_load("""
            if redisimpl.call("GET", KEYS[1]) == ARGV[1] then
              return redisimpl.call("PEXPIRE", KEYS[1], ARGV[2])
            else
              return 0
            end
        """)
        self._release_script_sha = self.r.script_load("""
            if redisimpl.call("GET", KEYS[1]) == ARGV[1] then
              return redisimpl.call("DEL", KEYS[1])
            else
              return 0
            end
        """)
        logging.info(f"Node {self.node_id}: Initialized.")

    @property
    def is_leader(self):
        return self._is_leader

    def _try_acquire_lock(self):
        """Attempts to acquire the leader lock."""
        # SET key value NX PX milliseconds
        # NX -- Only set the key if it does not already exist.
        # PX milliseconds -- Set the specified expiry time, in milliseconds.
        acquired = self.r.set(self.lock_key, self.node_id, nx=True, px=self.lease_duration_ms)
        if acquired:
            logging.info(f"Node {self.node_id}: Acquired leadership.")
            self._is_leader = True
            self._start_renewal_thread()
            return True
        return False

    def _renew_lease(self):
        """Periodically renews the lease if still the leader."""
        while not self._stop_event.is_set() and self._is_leader:
            try:
                # Use Lua script for conditional renewal
                # KEYS[1] = self.lock_key
                # ARGV[1] = self.node_id
                # ARGV[2] = self.lease_duration_ms
                renewed = self.r.evalsha(self._renew_script_sha, 1, self.lock_key, self.node_id, self.lease_duration_ms)
                if renewed == 1:  # PEXPIRE returns 1 on success, 0 if the key doesn't exist or value mismatch
                    logging.debug(f"Node {self.node_id}: Lease renewed successfully.")
                else:
                    logging.warning(f"Node {self.node_id}: Failed to renew lease. Stepping down.")
                    self._is_leader = False  # Lost leadership
                    break  # Stop renewal attempts
            except redis.exceptions.RedisError as e:
                logging.error(f"Node {self.node_id}: Redis error during lease renewal: {e}. Stepping down.")
                self._is_leader = False  # Assume lost leadership on error
                break
            except Exception as e:
                logging.error(f"Node {self.node_id}: Unexpected error during lease renewal: {e}. Stepping down.")
                self._is_leader = False
                break

            # Sleep, but check stop_event frequently enough to be responsive
            for _ in range(int(self.renewal_interval_s * 10)):  # Check 10 times per interval
                if self._stop_event.wait(0.1):
                    break
            if self._stop_event.is_set():
                break
        logging.info(f"Node {self.node_id}: Renewal thread stopping. Current leader status: {self._is_leader}")

    def _start_renewal_thread(self):
        if self._renewal_thread and self._renewal_thread.is_alive():
            return  # Already running

        self._stop_event.clear()
        self._renewal_thread = threading.Thread(target=self._renew_lease, name=f"Renewal-{self.node_id[:8]}")
        self._renewal_thread.daemon = True  # Allow the main program to exit even if the thread is running
        self._renewal_thread.start()
        logging.info(f"Node {self.node_id}: Renewal thread started.")

    def _stop_renewal_thread(self):
        self._stop_event.set()
        if self._renewal_thread and self._renewal_thread.is_alive():
            logging.debug(f"Node {self.node_id}: Waiting for renewal thread to stop...")
            self._renewal_thread.join(timeout=self.renewal_interval_s * 2)  # Wait a bit
            if self._renewal_thread.is_alive():
                logging.warning(f"Node {self.node_id}: Renewal thread did not stop in time.")
        self._renewal_thread = None
        logging.info(f"Node {self.node_id}: Renewal thread stopped.")

    def step_down(self):
        """Gracefully releases the leadership."""
        logging.info(f"Node {self.node_id}: Attempting to step down.")
        self._stop_renewal_thread()  # Stop trying to renew

        was_leader = self._is_leader
        self._is_leader = False  # Proactively mark as not leader

        if was_leader:  # Only try to release if we thought we were a leader
            try:
                # Use Lua script for conditional release
                # KEYS[1] = self.lock_key
                # ARGV[1] = self.node_id
                released = self.r.evalsha(self._release_script_sha, 1, self.lock_key, self.node_id)
                if released == 1:  # DEL returns 1 if the key was deleted, 0 if the key doesn't exist or value mismatch
                    logging.info(f"Node {self.node_id}: Released leadership successfully.")
                else:
                    logging.warning(f"Node {self.node_id}: Could not release lock (already lost or never had?).")
            except redis.exceptions.RedisError as e:
                logging.error(f"Node {self.node_id}: Redis error during step down: {e}")
            except Exception as e:
                logging.error(f"Node {self.node_id}: Unexpected error during step down: {e}")
        else:
            logging.info(f"Node {self.node_id}: Was not leader, no need to release lock explicitly.")

    def run_election_loop(self):
        """Main loop to try to become leader or perform leader/follower duties."""
        stop_main_loop = threading.Event()

        def signal_handler(signum, frame):
            logging.info(f"Node {self.node_id}: Signal {signum} received, shutting down.")
            stop_main_loop.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logging.info(f"Node {self.node_id}: Starting election loop.")
        try:
            while not stop_main_loop.is_set():
                if not self.is_leader:
                    if self._try_acquire_lock():
                        # Just became leader, _try_acquire_lock starts renewal
                        pass
                    else:
                        logging.info(
                            f"Node {self.node_id}: Still a follower. Checking again in {ELECTION_CHECK_INTERVAL_S}s.")
                        # Sleep, but check stop_main_loop frequently
                        for _ in range(
                                NUMBER_OF_TIMES_TO_CHECK_FOR_LEADER_PER_LEASE_DURATION):  # Check 10 times per interval
                            if stop_main_loop.wait(ELECTION_CHECK_INTERVAL_S):
                                break
                        if stop_main_loop.is_set():
                            break
                        continue  # Go back to check lock acquisition

                if self.is_leader:
                    # --- LEADER DUTY ---
                    logging.info(f"Node {self.node_id}: I AM THE LEADER. Performing leader duties...")
                    # Example: Do some work that only the leader should do
                    # For demonstration, just sleep. In a real app, this would be actual work.
                    self.leader_callback()  # Do work
                    if not self.is_leader:  # Check if we lost leadership during work
                        logging.warning(f"Node {self.node_id}: Lost leadership during leader duty.")
                        continue  # Re-evaluate leadership status
                    # --- END LEADER DUTY ---
                else:
                    # --- FOLLOWER DUTY (or waiting) ---
                    logging.info(f"Node {self.node_id}: I AM A FOLLOWER. Waiting...")
                    # Sleep, but check stop_main_loop frequently
                    for _ in range(
                            NUMBER_OF_TIMES_TO_CHECK_FOR_LEADER_PER_LEASE_DURATION):  # Check 10 times per interval
                        if stop_main_loop.wait(ELECTION_CHECK_INTERVAL_S):
                            break
                    if stop_main_loop.is_set():
                        break

        finally:
            logging.info(f"Node {self.node_id}: Exiting election loop.")
            self.step_down()  # Ensure we attempt to release the lock on exit
            if self.r:
                try:
                    self.r.close()  # Ensure Redis connection is closed
                except Exception as e:
                    logging.error(f"Node {self.node_id}: Error closing Redis connection: {e}")


if __name__ == "__main__":
    # To test, run this script in multiple terminals.
    # Only one should become the leader. If you kill the leader (Ctrl+C),
    # another one should take over after the lease expires or the election check interval.
    def leader_callback():
        logging.info("I am the leader. Doing work.")
        time.sleep(LEASE_DURATION_MS / 3 / 1000)


    def elect_leader(leader_callback: Callable):
        node_id = str(uuid.uuid4())  # Generate a unique ID for this instance
        logging.info(f"Starting instance with Node ID: {node_id}")

        try:
            r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            r_client.ping()
            logging.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            logging.error(f"Could not connect to Redis: {e}")
            return

        elector = RedisLeaderElector(
            redis_client=r_client,
            lock_key=LOCK_KEY,
            node_id=node_id,
            lease_duration_ms=LEASE_DURATION_MS,
            renewal_interval_s=RENEWAL_INTERVAL_S,
            leader_callback=leader_callback
        )

        elector.run_election_loop()
        logging.info(f"Node {node_id}: Application finished.")


    elect_leader(leader_callback=leader_callback)
