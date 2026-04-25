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

counter = 0
def build_event():
    global counter

    phase = (counter // 50) % 4
    counter += 1

    # --- Phase 0: Normal ---
    if phase == 0:
        latency = random.randint(50, 150)
        error = random.choice([0, 0, 0, 1])  # mostly no errors

    # --- Phase 1: Degradation ---
    elif phase == 1:
        latency = random.randint(150, 350)
        error = random.choice([0, 1])

    # --- Phase 2: Incident ---
    elif phase == 2:
        latency = random.randint(400, 600)
        error = random.choice([0, 1, 1])  # more errors

    # --- Phase 3: Recovery ---
    else:
        latency = random.randint(80, 200)
        error = random.choice([0, 0, 1])

    print(f"PHASE: {phase}")

    return {
        "service": "payments-api",
        "latency": latency,
        "error": error,
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