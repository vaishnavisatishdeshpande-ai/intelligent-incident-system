import pandas as pd


def load_nab_data(path):
    df = pd.read_csv(path)

    df = df.rename(columns={"value": "avg_latency"})
    df["avg_latency"] = df["avg_latency"] * 500

    df["latency_change"] = df["avg_latency"].diff().fillna(0)

    df["rolling_mean"] = df["avg_latency"].rolling(10).mean().fillna(df["avg_latency"])
    df["rolling_std"] = df["avg_latency"].rolling(10).std().fillna(0)

    df["error_rate"] = df["rolling_std"] / (df["rolling_mean"] + 1)

    df["failure"] = (
        (df["avg_latency"] > df["rolling_mean"] * 1.5) |
        (df["latency_change"] > 50) |
        (df["error_rate"] > 0.3)
    ).astype(int)

    return df[["avg_latency", "error_rate", "latency_change", "failure"]]