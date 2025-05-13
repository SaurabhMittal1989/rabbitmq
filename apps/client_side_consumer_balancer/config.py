import uuid

INSTANCE_ID_MAX = 10000
ELECTION_NODE = "ELECTION/"
STOP_FLAG = "STOP/"
ALLOCATION_NODE = "ALLOCATION/"

# ---  REDIS LEADER ELECTION Configuration ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
LOCK_KEY = "leader_election_lock"  # The Redis key used for the lock
LEASE_DURATION_MS = 10 * 1000  # 10 seconds: How long the lease is valid
RENEWAL_INTERVAL_S = LEASE_DURATION_MS / 1000 / 3  # Renew at 1/3 of the lease duration
NUMBER_OF_TIMES_TO_CHECK_FOR_LEADER_PER_LEASE_DURATION = 5
ELECTION_CHECK_INTERVAL_S = LEASE_DURATION_MS / 1000 / NUMBER_OF_TIMES_TO_CHECK_FOR_LEADER_PER_LEASE_DURATION  # How often non-leaders check if they can become leader


#REDIS Follower:
UUID = uuid.uuid4()
CONFIG_KEY = f"consumer:queues_config:{UUID}"
# CONFIG_KEY = f"consumer:queues_config:123"
print("CONFIG KEY CHANGES: ", CONFIG_KEY)
REDIS_DB_NUMBER = 0


#RABBIT_MQ
RABBIT_MQ_HOST='localhost'
# Define example exchange and queue
RABBIT_MQ_EXCHANGE_NAME = "my_exchange"
RABBIT_MQ_QUEUE_NAME = "q0002"
RABBITMQ_PREFETCH_COUNT=1


REGISTER_KEY_BASE = "consumer:participants:membership" # Changed from leader_participants for clarity
DEFAULT_REGISTRATION_TTL_SECONDS = 60  # Time-to-live for the registration in seconds
RENEWAL_INTERVAL_FACTOR = 0.75 # Renew at 75% of TTL

# Lua script content (same as defined above)
RENEW_REGISTRATION_LUA_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("PEXPIRE", KEYS[1], ARGV[2])
else
  return 0
end
"""
# Value to store in Redis for the registration key. Could be consumer_id or a simple marker.
REGISTRATION_VALUE_MARKER = "active"