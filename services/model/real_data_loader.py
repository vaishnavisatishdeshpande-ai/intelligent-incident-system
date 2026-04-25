import pandas as pd


def load_nab_data(path):
    """
    Load NAB dataset and generate realistic system signals
    using data-driven thresholds.
    """

    df = pd.read_csv(path)

    # Rename
    df = df.rename(columns={
        "value": "latency"
    })

    # Normalize
    df["latency"] = df["latency"] / df["latency"].max() * 500

    # -----------------------------
    # 🔥 DATA-DRIVEN THRESHOLDS
    # -----------------------------

    high_threshold = df["latency"].quantile(0.90)
    extreme_threshold = df["latency"].quantile(0.95)

    # -----------------------------
    # Features
    # -----------------------------

    # Error = high spike
    df["error"] = (df["latency"] > high_threshold).astype(int)

    # Rolling mean for temporal behavior
    df["rolling_mean"] = df["latency"].rolling(window=5).mean()

    # Failure = extreme + sustained
    df["failure"] = (
        (df["latency"] > extreme_threshold) &
        (df["rolling_mean"] > high_threshold)
    ).astype(int)

    # Clean NaNs
    df = df.dropna()

    # Final schema
    df = df[["latency", "error", "failure"]]

    return df