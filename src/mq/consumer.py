import threading
import time

from src.config import q1, q2
from src.mq.utils import instantiate_exchange_and_queues, get_queue_names

threads = []


def consumer(q):
    """ Start parallel consumer on different threads: Listening  to queues is a blocking call"""
    ch = instantiate_exchange_and_queues()

    def callback(ch, method, properties, body):
        """Process function : on message callback"""
        time.sleep(4)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Received: {threading.current_thread().name} :  {body}")

    ch.basic_consume(queue=q, on_message_callback=callback, )
    ch.basic_qos(prefetch_count=1)
    ch.start_consuming()


def start_consumers():
    """start consumers, 1 each for a queue"""
    qs = get_queue_names(q1, q2)
    consumer_threads = [threading.Thread(target=consumer, args=(q,), name=f"Thread-{q}") for q in qs]
    start = [thread.start() for thread in consumer_threads]

    # TODO restart consumers when the program returns :consumer crashes!
    wait = [thread.join() for thread in consumer_threads]


if __name__ == "__main__":
    start_consumers()
