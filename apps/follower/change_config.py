import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
config_key = "consumer:queues_config"

def update_queue_config(new_queues_list, follower_id=0):
    new_config = {"queues": new_queues_list}
    config_key_new = config_key + ":" +  str(follower_id)
    r.set(config_key_new, json.dumps(new_config))
    print(f"Updated '{config_key_new}' with: {new_config}")

# Example usage:
update_queue_config(["1", "2"], follower_id=1)
update_queue_config(["2"], follower_id=2)
update_queue_config(["4"], follower_id=3)