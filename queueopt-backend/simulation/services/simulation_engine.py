import time
import random
from datetime import datetime


def run_simulation(config: dict) -> tuple[dict, dict]:
    """
    Stub simulation engine.
    Replace this with real queueing logic later.

    Returns:
    (results_json, metadata_json)
    """

    start_time = datetime.utcnow()
    start_ms = time.time()

    # Fake wait to simulate a process
    time.sleep(0.5)

    # ----- Sample output structure (matches PDF) -----
    results = {
        "performance_metrics": {
            "avg_waiting_time": round(random.uniform(5, 30), 2),
            "avg_dining_time": round(random.uniform(40, 90), 2),
            "customers_served": random.randint(50, 200),
            "customers_lost": random.randint(0, 20),
        },
        "utilization_metrics": {
            "table_utilization": round(random.uniform(40, 95), 2),
            "server_utilization": round(random.uniform(40, 95), 2),
            "peak_load": random.randint(20, 50),
        },
        "queue_length_stats": [
            {"time": i * 60, "queue_length": random.randint(0, 20)}
            for i in range(1, 11)
        ],
        "service_distribution": {
            "party_size_distribution": config.get("party_size_distribution", {}),
            "service_time_params": config.get("service_time_params", {}),
        },
    }

    execution_time_ms = int((time.time() - start_ms) * 1000)

    metadata = {
        "execution_time_ms": execution_time_ms,
        "simulation_start_time": start_time.isoformat() + "Z",
        "simulation_end_time": datetime.utcnow().isoformat() + "Z",
        "random_seed": None,
        "version": "1.0.0",
    }

    return results, metadata
