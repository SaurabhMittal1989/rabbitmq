import time


class FollowerBusinessLogic:
    def process_job_callback(self, body):
        time.sleep(2)
        print(f"Follower job processing: {body}")
