from kafka import KafkaProducer
import json
import time
import random

from services.producer.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, SERVICE_NAME


def create_producer():
    print("Creating producer...")
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print("Producer created")
    return producer


def build_event():
    print("Building event...")
    return {
        "service": SERVICE_NAME,
        "latency": 120,
        "error": 0
    }


def send_event(producer, event):
    print("Sending event...")
    producer.send(KAFKA_TOPIC, event)
    producer.flush()
    print("Event sent!")


import time
import random


def main():
    print("Starting producer...")
    producer = create_producer()

    while True:
        event = {
            "service": SERVICE_NAME,
            "latency": random.randint(50, 600),
            "error": random.choice([0, 1])
        }

        send_event(producer, event)
        print("Sent:", event)

        time.sleep(1)


if __name__ == "__main__":
    main()