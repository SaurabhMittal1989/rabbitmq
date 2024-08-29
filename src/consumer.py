import threading
import time

from src.config import q1, q2
from src.utils import instantiate_exchange_and_queue, get_queue_name

threads = []


def consumer(q):
    ch = instantiate_exchange_and_queue()

    def callback(ch, method, properties, body):
        time.sleep(4)
        print(f"Received: {method}, {properties}, {body}")

    ch.basic_consume(queue=q, on_message_callback=callback, auto_ack=True, )
    ch.start_consuming()


def start_consumers():
    qs = get_queue_name(q1, q2)
    consumer_threads = [threading.Thread(target=consumer, args=(q,)) for q in qs]
    start = [thread.start() for thread in consumer_threads]
    wait = [thread.join() for thread in consumer_threads]


if __name__ == "__main__":
    start_consumers()
