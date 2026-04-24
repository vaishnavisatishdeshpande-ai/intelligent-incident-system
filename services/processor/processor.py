from kafka import KafkaConsumer
import json
from collections import deque

from services.producer.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


# sliding window to store last N events
WINDOW_SIZE = 10


class FeatureEngine:
    def __init__(self):
        self.events = deque(maxlen=WINDOW_SIZE)

    def add_event(self, event):
        self.events.append(event)

    def compute_features(self):
        if not self.events:
            return None

        latencies = [e["latency"] for e in self.events]
        errors = [e["error"] for e in self.events]

        avg_latency = sum(latencies) / len(latencies)
        error_rate = sum(errors) / len(errors)

        return {
            "avg_latency": avg_latency,
            "error_rate": error_rate
        }


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest'
    )


def main():
    print("Starting processor...")

    consumer = create_consumer()
    engine = FeatureEngine()

    for message in consumer:
        event = message.value
        print("Received event:", event)

        engine.add_event(event)
        features = engine.compute_features()

        if features:
            print("Computed features:", features)


if __name__ == "__main__":
    main()