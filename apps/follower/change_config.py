import redis
import json
import uuid
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
config_key = "consumer:queues_config"

# Lua script for atomic update and signal
LUA_SCRIPT_UPDATE_AND_SIGNAL = """
    local config_key = KEYS[1]
    local signal_key = KEYS[2]
    local config_value = ARGV[1]
    local signal_value = ARGV[2]

    redis.call('SET', config_key, config_value)
    redis.call('LPUSH', signal_key, signal_value)
    return 1
"""

def update_queue_config_atomic_longpoll(follower_id, new_queues_list):
    config_key = f"consumer:queues_config:{follower_id}"
    signal_key = f"consumer:config_update_signal:{follower_id}"
    version = str(uuid.uuid4())
    new_config_json = json.dumps({"queues": new_queues_list, "version": version})

    # Register script if not done, or do it once at app startup
    if not hasattr(update_queue_config_atomic_longpoll, 'sha'):
        update_queue_config_atomic_longpoll.sha = r.script_load(LUA_SCRIPT_UPDATE_AND_SIGNAL)

    try:
        r.evalsha(update_queue_config_atomic_longpoll.sha, 2, config_key, signal_key, new_config_json, version)
        print(f"Atomically updated '{config_key}' (v: {version}), signaled '{signal_key}'.")
    except redis.exceptions.NoScriptError: # Script not in cache, load and retry
        print("Lua script not found in cache, loading and retrying...")
        update_queue_config_atomic_longpoll.sha = r.script_load(LUA_SCRIPT_UPDATE_AND_SIGNAL)
        r.evalsha(update_queue_config_atomic_longpoll.sha, 2, config_key, signal_key, new_config_json, version)
        print(f"Atomically updated '{config_key}' (v: {version}), signaled '{signal_key}'. (after reload)")
    return version

def update_queue_config(new_queues_list, follower_id=0):
    new_config = {"queues": new_queues_list}
    config_key_new = config_key + ":" +  str(follower_id)
    r.set(config_key_new, json.dumps(new_config))
    print(f"Updated '{config_key_new}' with: {new_config}")

# Example usage:
update_queue_config_atomic_longpoll(1, ["q0001"])
update_queue_config_atomic_longpoll('123', ["q0002"])
update_queue_config_atomic_longpoll(3, ["q0003", "q0004"])
# update_queue_config(["4"], follower_id=3)