import time

import pika
from src.config import exchange_name, q1, q2


def create_channel():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    ch = connection.channel()
    return ch


def create_exchange():
    ch = create_channel()
    ch.exchange_declare(exchange='usn',
                        exchange_type='x-consistent-hash',
                        durable=True)
    return ch


def make_queue(m, n):
    ch = create_channel()
    qs = get_queue_name(q1=m, q2=n)
    for q in qs:
        ch.queue_declare(queue=q, durable=True, auto_delete=False, )
        ch.queue_bind(exchange=exchange_name, queue=q, routing_key=str(1))
        print(f"Creating queue: {q}")
    ch.close()


def publish(m, n):
    """Publish messages with routing keys m to n"""
    ch = create_channel()
    for rk in list(map(lambda s: str(s), range(m, n + 1))):
        ch.basic_publish(exchange=exchange_name, routing_key='100', body=f"Hello{rk}")
        time.sleep(0.01)
        print(f'Published: exchange={exchange_name}, routing_key={rk}, body="Hello{rk}"')

    time.sleep(10)
    ch.close()


def instantiate_exchange_and_queue():
    ch = create_exchange()
    make_queue(q1, q2)
    return ch


def get_queue_name(q1, q2):
    return list(map(lambda s: "q%04d" % s, range(q1, q2 + 1)))
