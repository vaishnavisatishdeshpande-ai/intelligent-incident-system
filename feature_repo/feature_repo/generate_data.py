import sys
import os
sys.path.append("/Users/vaishnavideshpande/PycharmProjects/PythonProject/intelligent-incident-system")

import pandas as pd
from datetime import datetime, timedelta
from services.processor.processor import FeatureEngine

engine = FeatureEngine()

rows = []
start_time = datetime.utcnow()

for i in range(200):
    event = {
        "service": "payments-api",
        "latency": 200 + (i % 50),
        "error": i % 2
    }

    engine.add_event(event)
    features = engine.compute_features()

    if features:
        rows.append({
            "service": "payments-api",
            "event_timestamp": start_time + timedelta(seconds=i),
            "avg_latency": features["avg_latency"],
            "error_rate": features["error_rate"],
            "latency_change": features["latency_change"],
        })

df = pd.DataFrame(rows)
df.to_parquet("data/features.parquet", index=False)