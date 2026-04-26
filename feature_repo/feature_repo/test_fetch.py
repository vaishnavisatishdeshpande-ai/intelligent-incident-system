from feast import FeatureStore

store = FeatureStore(repo_path=".")

features = store.get_online_features(
    features=[
        "incident_features:avg_latency",
        "incident_features:error_rate",
        "incident_features:latency_change",
    ],
    entity_rows=[{"service": "payments-api"}],
).to_dict()

print(features)