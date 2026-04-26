from feast import Project
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32
from datetime import timedelta

event = Entity(
    name="service",
    join_keys=["service"],
)

source = FileSource(
    path="data/features.parquet",
    timestamp_field="event_timestamp",
)

feature_view = FeatureView(
    name="incident_features",
    entities=[event],
    ttl=timedelta(days=1),
    schema=[
        Field(name="avg_latency", dtype=Float32),
        Field(name="error_rate", dtype=Float32),
        Field(name="latency_change", dtype=Float32),
    ],
    source=source,
)
project = Project(name="feature_repo")