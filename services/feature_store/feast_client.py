from feast import FeatureStore


class FeastClient:
    def __init__(self):
        self.store = FeatureStore(repo_path="feature_repo/feature_repo")

    def get_features(self, service: str):
        try:
            result = self.store.get_online_features(
                features=[
                    "incident_features:avg_latency",
                    "incident_features:error_rate",
                    "incident_features:latency_change",
                ],
                entity_rows=[{"service": service}],
            ).to_dict()

            avg = result.get("avg_latency", [None])[0]
            err = result.get("error_rate", [None])[0]
            change = result.get("latency_change", [None])[0]

            if avg is None or err is None:
                return None

            return {
                "avg_latency": avg,
                "error_rate": err,
                "latency_change": change if change is not None else 0.0,
            }

        except Exception:
            return None