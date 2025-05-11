# Example in Python (using redis-py) - Consumer
import redis
import json
import threading
import time

class QueueConsumer:
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, follower_id=0):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        self.config_key = f"consumer:queues_config:{follower_id}"
        self.current_subscribed_queues = set()
        self.redis_db_num = redis_db # Important for constructing the notification channel name

        # Initial load of configuration
        self._load_and_apply_config()

        # Start listening for notifications in a separate thread
        self.notification_thread = threading.Thread(target=self._listen_for_config_changes, daemon=True)
        self.notification_thread.start()

    def _fetch_config(self):
        config_json = self.redis_client.get(self.config_key)
        if config_json:
            try:
                config_data = json.loads(config_json)
                return set(config_data.get("queues", []))
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{self.config_key}'")
                return set() # Return empty set on error
        return set() # Key doesn't exist or empty

    def _load_and_apply_config(self, event_type="initial_load"):
        print(f"Config change detected (event: {event_type}), reloading...")
        new_queues_to_subscribe = self._fetch_config()

        queues_to_add = new_queues_to_subscribe - self.current_subscribed_queues
        queues_to_remove = self.current_subscribed_queues - new_queues_to_subscribe

        for q_name in queues_to_add:
            self._subscribe_to_queue(q_name)
        for q_name in queues_to_remove:
            self._unsubscribe_from_queue(q_name)

        self.current_subscribed_queues = new_queues_to_subscribe
        print(f"Current subscribed queues: {self.current_subscribed_queues}")

    def _subscribe_to_queue(self, queue_name):
        # Replace with your actual queue subscription logic
        print(f"Subscribing to queue: {queue_name}")
        # e.g., self.message_broker_client.subscribe(queue_name, self.on_message_callback)

    def _unsubscribe_from_queue(self, queue_name):
        # Replace with your actual queue unsubscription logic
        print(f"Unsubscribing from queue: {queue_name}")
        # e.g., self.message_broker_client.unsubscribe(queue_name)

    def _listen_for_config_changes(self):
        # Construct the keyspace notification channel name
        # __keyspace@<db>__:<key>
        notification_channel = f"__keyspace@{self.redis_db_num}__:{self.config_key}"
        self.pubsub.subscribe(notification_channel)
        print(f"Listening for changes on Redis key: '{self.config_key}' via channel '{notification_channel}'")

        for message in self.pubsub.listen():
            # message format: {'type': 'message', 'pattern': None, 'channel': b'__keyspace@0__:consumer:queues_config', 'data': b'set'}
            print(f"Received notification: {message}")
            if message['type'] == 'message':
                event_type = message['data'] # e.g., "set", "del"
                key_affected = message['channel'].split(':', 1)[1] # Extract key from channel name if using psubscribe, not needed here

                if event_type in ["set", "hset"]: # Or other relevant commands like 'hset' if using hashes
                    self._load_and_apply_config(event_type)
                elif event_type == "del":
                    print(f"Configuration key '{self.config_key}' was deleted.")
                    # Decide what to do: unsubscribe all, or revert to a default
                    self._load_and_apply_config(event_type) # This will fetch an empty config
                # You might also want to handle 'expired' if your keys can expire

    def stop(self):
        print("Stopping consumer...")
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        # Unsubscribe from all queues before exiting
        for q_name in list(self.current_subscribed_queues): # Iterate over a copy
            self._unsubscribe_from_queue(q_name)
        self.current_subscribed_queues.clear()
        print("Consumer stopped.")


# --- Example Usage ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--follower_id', required=True)
    args = parser.parse_args()
    consumer = QueueConsumer(redis_db=0, follower_id=args.follower_id) # Assuming Redis DB 0

    print("Consumer started. It will react to changes in the Redis key 'consumer:queues_config'.")
    print("Try updating the key in another terminal using redis-cli or the updater script.")
    print("Example: redis-cli SET consumer:queues_config '{\"queues\": [\"q1\", \"q2\"]}'")
    print("Example: redis-cli DEL consumer:queues_config")

    try:
        while True:
            # Keep the main thread alive, or do other work
            time.sleep(1)
            # In a real app, this might be where your consumer processes messages from its subscribed queues
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        consumer.stop()