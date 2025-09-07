import time
import uuid

import redis
LEADER_TENURE = 2

class RedisLeaderElection:
    def __init__(self, redis_client, lock_key='leader_lock', ttl=LEADER_TENURE, participants_key='leader_participants'):
        self.redis = redis_client
        self.lock_key = lock_key
        self.ttl = ttl
        self.participants_key = participants_key
        self.identifier = str(uuid.uuid4())  # Unique ID per instance

        self.register_participant()

    def register_participant(self):
        self.redis.sadd(self.participants_key, self.identifier)

    def list_participants(self):
        return [id.decode() for id in self.redis.smembers(self.participants_key)]

    def try_to_be_leader(self):
        result = self.redis.set(self.lock_key, self.identifier, nx=True, ex=self.ttl)
        return result is True

    def is_leader(self):
        current_leader = self.redis.get(self.lock_key)
        return current_leader and current_leader.decode() == self.identifier

    def renew_leadership(self):
        if self.is_leader():
            self.redis.expire(self.lock_key, self.ttl)
            return True
        return False

    def resign(self):
        if self.is_leader():
            self.redis.delete(self.lock_key)

    def leader_callback(self):
        i = 0;
        while True:
            i = i +1
            print(f" I am the leader: {i}: {self.identifier}")
            time.sleep(LEADER_TENURE/3)
            self.renew_leadership()
            print("Participants in the election:", self.list_participants())


    def follower_callback(self):
        i = 0;
        while True:
            i = i +1
            print(f" I am the follower: {i}: {self.identifier}")
            time.sleep(2)
            print("Participants in the election:", self.list_participants())


    def keep_working(self):
        if self.is_leader():
            self.leader_callback()
        else:
            self.follower_callback()




if __name__ == '__main__':


    r = redis.Redis(host='localhost', port=6379, decode_responses=False)
    election = RedisLeaderElection(r)
    election.keep_working()


