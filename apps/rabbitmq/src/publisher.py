#!/usr/bin/env python
import argparse

from apps.rabbitmq.src.utils import publish, instantiate_exchange_and_queues


def start_publisher(m1, m2):
    instantiate_exchange_and_queues()
    publish(m1, m2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--m1', default=1, type=int, help='message routing key start')
    parser.add_argument('--m2', default=1000, type=int, help='message routing key end')
    args = parser.parse_args()
    m1, m2 = args.m1, args.m2
    start_publisher(m1, m2)
