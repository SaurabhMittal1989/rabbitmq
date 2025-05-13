import redis
import time
import threading
import logging

from apps.client_side_consumer_balancer.Register import IRegister
from apps.client_side_consumer_balancer.config import *
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Register(IRegister):
    def __init__(self, redis_client: redis.Redis, consumer_id: str,
                 registration_key_base: str = REGISTER_KEY_BASE,
                 ttl_seconds: int = DEFAULT_REGISTRATION_TTL_SECONDS):
        """
        Initializes the ConsumerRegistration instance.

        Args:
            redis_client: An initialized Redis client instance.
            consumer_id: A unique ID for this consumer. If None, a UUID will be generated.
            registration_key_base: The base string for the Redis registration key.
            ttl_seconds: The time-to-live for the registration in seconds.
        """
        if not isinstance(redis_client, redis.Redis):
            raise TypeError("redis_client must be an instance of redis.Redis")

        self.r = redis_client
        self.consumer_id = consumer_id
        self.registration_key = f"{registration_key_base}:{self.consumer_id}"
        self.registration_ttl_ms = ttl_seconds * 1000
        self.renewal_interval_seconds = ttl_seconds * RENEWAL_INTERVAL_FACTOR

        self._is_registered = False
        self._stop_event = threading.Event()
        self._renewal_thread = None

        try:
            self._renew_script_sha = self.r.script_load(RENEW_REGISTRATION_LUA_SCRIPT)
            logging.info(f"Consumer {self.consumer_id}: Lua script for renewal loaded with SHA: {self._renew_script_sha}")
        except redis.exceptions.RedisError as e:
            logging.error(f"Consumer {self.consumer_id}: Failed to load Lua script: {e}")
            raise  # Propagate error if script loading fails

    def _perform_registration(self) -> bool:
        """
        Attempts to register the consumer in Redis by setting the key with a TTL.
        """
        try:
            # SET key value PX milliseconds
            # We use REGISTRATION_VALUE_MARKER as the value.
            # The Lua script will check for this value during renewal.
            success = self.r.set(
                self.registration_key,
                REGISTRATION_VALUE_MARKER,
                px=self.registration_ttl_ms
            )
            if success:
                logging.info(f"Consumer {self.consumer_id}: Successfully registered with key '{self.registration_key}'.")
                return True
            else:
                # This path is unlikely for a simple SET unless there's a Redis issue
                # or a transaction problem not covered here.
                logging.warning(f"Consumer {self.consumer_id}: Failed to set registration key '{self.registration_key}'.")
                return False
        except redis.exceptions.RedisError as e:
            logging.error(f"Consumer {self.consumer_id}: Redis error during initial registration: {e}")
            return False
        except Exception as e:
            logging.error(f"Consumer {self.consumer_id}: Unexpected error during initial registration: {e}")
            return False

    def _renew_registration_loop(self):
        """Periodically renews the registration if still marked as registered."""
        logging.info(f"Consumer {self.consumer_id}: Starting registration renewal loop for key '{self.registration_key}'.")
        while not self._stop_event.is_set():
            if not self._is_registered: # Could be set to False by stop() or if renewal fails
                logging.info(f"Consumer {self.consumer_id}: No longer registered. Stopping renewal loop.")
                break
            try:
                # KEYS[1] = self.registration_key
                # ARGV[1] = REGISTRATION_VALUE_MARKER (expected value)
                # ARGV[2] = self.registration_ttl_ms
                renewed = self.r.evalsha(
                    self._renew_script_sha,
                    1, # Number of keys
                    self.registration_key,
                    REGISTRATION_VALUE_MARKER,
                    self.registration_ttl_ms
                )
                if renewed == 1:
                    logging.debug(f"Consumer {self.consumer_id}: Registration renewed successfully for key '{self.registration_key}'.")
                else:
                    # This means the key either didn't exist or its value didn't match.
                    # This could happen if the key expired before renewal or was manually deleted/altered.
                    logging.warning(f"Consumer {self.consumer_id}: Failed to renew registration for key '{self.registration_key}'. Registration lost. Value mismatch or key expired.")
                    self._is_registered = False # Lost registration
                    # Attempt to re-register immediately.
                    # If re-registration fails, the loop will break due to _is_registered being False.
                    if self._perform_registration():
                        self._is_registered = True
                        logging.info(f"Consumer {self.consumer_id}: Re-registered successfully after renewal failure.")
                    else:
                        logging.error(f"Consumer {self.consumer_id}: Failed to re-register after renewal failure. Stopping.")
                        break # Stop renewal attempts

            except redis.exceptions.NoScriptError:
                logging.warning(f"Consumer {self.consumer_id}: Lua script SHA {self._renew_script_sha} not found. Reloading script.")
                try:
                    self._renew_script_sha = self.r.script_load(RENEW_REGISTRATION_LUA_SCRIPT)
                    logging.info(f"Consumer {self.consumer_id}: Lua script reloaded successfully.")
                except redis.exceptions.RedisError as e_load:
                    logging.error(f"Consumer {self.consumer_id}: Failed to reload Lua script: {e_load}. Stopping renewal.")
                    self._is_registered = False
                    break
            except redis.exceptions.RedisError as e:
                logging.error(f"Consumer {self.consumer_id}: Redis error during registration renewal: {e}. Assuming registration lost.")
                self._is_registered = False # Assume lost registration on error
                break
            except Exception as e:
                logging.error(f"Consumer {self.consumer_id}: Unexpected error during registration renewal: {e}. Assuming registration lost.")
                self._is_registered = False
                break

            # Wait for the next renewal interval or until stop_event is set
            # self._stop_event.wait() returns True if the event is set, False on timeout
            if self._stop_event.wait(self.renewal_interval_seconds):
                break # Stop event was set

        logging.info(f"Consumer {self.consumer_id}: Registration renewal loop stopped for key '{self.registration_key}'.")

    def register(self) -> bool:
        """
        Registers the consumer and starts the periodic renewal process.
        Returns True if initial registration is successful, False otherwise.
        """
        if self._is_registered:
            logging.warning(f"Consumer {self.consumer_id}: Already registered and renewal process active.")
            return True

        if self._perform_registration():
            self._is_registered = True
            self._stop_event.clear() # Ensure stop event is clear before starting thread
            self._renewal_thread = threading.Thread(target=self._renew_registration_loop, daemon=True)
            self._renewal_thread.start()
            logging.info(f"Consumer {self.consumer_id}: Registration renewal thread started.")
            return True
        else:
            logging.error(f"Consumer {self.consumer_id}: Initial registration failed. Renewal thread not started.")
            return False

    def stop(self):
        """
        Stops the registration renewal process and attempts to unregister the consumer.
        """
        logging.info(f"Consumer {self.consumer_id}: Stopping registration process...")
        self._stop_event.set()
        self._is_registered = False # Mark as not registered

        if self._renewal_thread and self._renewal_thread.is_alive():
            logging.debug(f"Consumer {self.consumer_id}: Waiting for renewal thread to join...")
            self._renewal_thread.join(timeout=self.renewal_interval_seconds * 2) # Wait a bit for thread to finish
            if self._renewal_thread.is_alive():
                logging.warning(f"Consumer {self.consumer_id}: Renewal thread did not join in time.")
        self._renewal_thread = None

        try:
            # Best effort to clean up the registration key
            deleted_count = self.r.delete(self.registration_key)
            if deleted_count > 0:
                logging.info(f"Consumer {self.consumer_id}: Successfully unregistered (deleted key '{self.registration_key}').")
            else:
                logging.info(f"Consumer {self.consumer_id}: Registration key '{self.registration_key}' not found or already deleted during unregistration.")
        except redis.exceptions.RedisError as e:
            logging.error(f"Consumer {self.consumer_id}: Redis error during unregistration: {e}")
        except Exception as e:
            logging.error(f"Consumer {self.consumer_id}: Unexpected error during unregistration: {e}")
        logging.info(f"Consumer {self.consumer_id}: Registration process stopped.")

    def is_registered(self) -> bool:
        """
        Checks if the consumer believes it is currently registered.
        Note: This is the local state, actual Redis state might differ briefly.
        """
        return self._is_registered

    def __del__(self):
        # Ensure stop is called if the object is garbage collected,
        # though explicit stop() is preferred.
        if self._is_registered or (self._renewal_thread and self._renewal_thread.is_alive()):
            logging.warning(f"Consumer {self.consumer_id}: Object being deleted without explicit stop. Attempting cleanup.")
            self.stop()

# --- Example Usage ---
if __name__ == "__main__":
    # Make sure you have a Redis server running locally or provide connection details
    try:
        redis_host = 'localhost'
        redis_port = 6379
        r_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r_client.ping() # Test connection
        logging.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Could not connect to Redis: {e}")
        exit(1)

    # Create and start a consumer registration
    # Shorter TTL for easier testing
    consumer_reg1 = Register(r_client, consumer_id="consumer-alpha", ttl_seconds=10)
    if consumer_reg1.register():
        logging.info(f"Consumer {consumer_reg1.consumer_id} started successfully.")
    else:
        logging.error(f"Failed to start consumer {consumer_reg1.consumer_id}.")
        exit(1)

    # Create another consumer
    consumer_reg2 = Register(r_client, consumer_id="consumer-beta", ttl_seconds=12)
    if consumer_reg2.register():
        logging.info(f"Consumer {consumer_reg2.consumer_id} started successfully.")
    else:
        logging.error(f"Failed to start consumer {consumer_reg2.consumer_id}.")
        # Don't exit, let consumer1 run

    try:
        # Keep the main thread alive to observe renewals
        # In a real application, this would be your main application loop
        for i in range(30): # Run for ~30 seconds
            time.sleep(1)
            logging.info(f"Main loop: {consumer_reg1.consumer_id} is_registered: {consumer_reg1.is_registered()}, {consumer_reg2.consumer_id} is_registered: {consumer_reg2.is_registered()}")
            if not consumer_reg1.is_registered() and not consumer_reg2.is_registered():
                logging.info("Both consumers seem to have lost registration. Exiting example.")
                break

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down...")
    finally:
        logging.info("Stopping consumer registrations...")
        consumer_reg1.stop()
        consumer_reg2.stop()
        logging.info("Example finished.")

    # To verify in redis-cli:
    # SCAN 0 MATCH consumer:participants:membership:*
    # GET consumer:participants:membership:consumer-alpha
    # TTL consumer:participants:membership:consumer-alpha