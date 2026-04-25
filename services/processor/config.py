LATENCY_THRESHOLD = 300
ERROR_RATE_THRESHOLD = 0.3

# spike detection sensitivity
LATENCY_SPIKE_DELTA = 120      # e.g., jump of +120ms vs previous window
ERROR_SPIKE_DELTA = 0.15       # e.g., +15% jump

# optional: minimum samples before detection
MIN_WINDOW_SIZE = 5