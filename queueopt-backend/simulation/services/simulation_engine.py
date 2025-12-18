import time
import math
import random
from datetime import datetime
from typing import Dict, Any, Tuple, List


def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def calculate_weighted_service_time(
    party_size_distribution: Dict[str, float],
    service_time_params: Dict[str, Any]
) -> float:
    """
    Calculate weighted average service time based on party size distribution.
    
    Args:
        party_size_distribution: Dict mapping party size (as string) to probability
            e.g., {"1": 0.05, "2": 0.40, "3": 0.10, "4": 0.30, ...}
        service_time_params: Dict with mean_by_party_size mapping
            e.g., {"mean_by_party_size": {"1-2": 45, "3-4": 60, "5-6": 75, "7+": 90}}
    
    Returns:
        Weighted average service time in minutes
    """
    if not party_size_distribution or not service_time_params:
        # Default fallback
        mean_by_party_size = service_time_params.get("mean_by_party_size", {}) if service_time_params else {}
        return mean_by_party_size.get("1-2", 45.0)
    
    mean_by_party_size = service_time_params.get("mean_by_party_size", {})
    
    # Map party sizes to service time buckets
    def get_party_bucket(party_size: int) -> str:
        """Map numeric party size to bucket key."""
        if party_size <= 2:
            return "1-2"
        elif party_size <= 4:
            return "3-4"
        elif party_size <= 6:
            return "5-6"
        else:
            return "7+"
    
    # Calculate weighted average
    total_weighted_time = 0.0
    total_probability = 0.0
    
    for party_size_str, probability in party_size_distribution.items():
        try:
            party_size = int(party_size_str)
            bucket = get_party_bucket(party_size)
            service_time = mean_by_party_size.get(bucket, 45.0)  # Default 45 if bucket missing
            
            total_weighted_time += service_time * probability
            total_probability += probability
        except (ValueError, TypeError):
            # Skip invalid entries
            continue
    
    # Normalize by total probability (should be ~1.0)
    if total_probability > 0:
        return total_weighted_time / total_probability
    else:
        # Fallback to default
        return mean_by_party_size.get("1-2", 45.0)


def apply_queue_strategy(
    base_metrics: Dict[str, Any],
    queue_strategy: str,
    party_size_distribution: Dict[str, float],
    avg_service_time: float
) -> Dict[str, Any]:
    """
    Apply queue strategy adjustments to base metrics.
    
    Strategies:
    - fcfs: First-Come-First-Served (no adjustment)
    - priority_small: Small parties get priority (faster turnover, better utilization)
    - priority_large: Large parties get priority (optimize table use, longer waits)
    - dynamic: Adaptive strategy (balance between strategies)
    
    Args:
        base_metrics: Base metrics from M/M/c calculation
        queue_strategy: Strategy name
        party_size_distribution: Party size distribution
        avg_service_time: Average service time
    
    Returns:
        Adjusted metrics dictionary
    """
    adjusted = base_metrics.copy()
    
    if queue_strategy == "fcfs":
        # No adjustment for FCFS
        strategy_multiplier = 1.0
        utilization_boost = 1.0
        
    elif queue_strategy == "priority_small":
        # Small parties first: faster turnover, better utilization
        # Reduces wait time by ~10-15%, improves utilization by ~5-10%
        strategy_multiplier = 0.85  # 15% reduction in wait time
        utilization_boost = 1.08  # 8% improvement in utilization
        
    elif queue_strategy == "priority_large":
        # Large parties first: optimize table use, but longer waits for small parties
        # Increases wait time by ~10-15%, improves table utilization by ~10-15%
        strategy_multiplier = 1.12  # 12% increase in wait time
        utilization_boost = 1.12  # 12% improvement in table utilization
        
    elif queue_strategy == "dynamic":
        # Dynamic: Adaptive strategy that balances between strategies
        # Moderate improvements across the board
        strategy_multiplier = 0.95  # 5% reduction in wait time
        utilization_boost = 1.05  # 5% improvement in utilization
        
    else:
        # Unknown strategy, use FCFS
        strategy_multiplier = 1.0
        utilization_boost = 1.0
    
    # Apply strategy adjustments
    adjusted["avg_wait_time"] = max(0, adjusted["avg_wait_time"] * strategy_multiplier)
    adjusted["max_wait_time"] = max(0, adjusted["max_wait_time"] * strategy_multiplier)
    
    # Adjust queue length proportionally
    adjusted["Lq"] = max(0, adjusted["Lq"] * strategy_multiplier)
    
    # Adjust utilization metrics
    adjusted["table_utilization"] = min(0.95, adjusted["table_utilization"] * utilization_boost)
    adjusted["server_utilization"] = min(0.95, adjusted["server_utilization"] * utilization_boost)
    adjusted["peak_table_utilization"] = min(0.98, adjusted["peak_table_utilization"] * utilization_boost)
    adjusted["peak_server_utilization"] = min(0.98, adjusted["peak_server_utilization"] * utilization_boost)
    
    # Recalculate customers served/lost based on new wait time
    # Better strategies reduce reneging
    if strategy_multiplier < 1.0:
        # Better wait time = fewer lost customers
        renege_reduction = (1.0 - strategy_multiplier) * 0.3  # Up to 30% reduction in reneging
        adjusted["customers_lost"] = max(0, int(adjusted["customers_lost"] * (1 - renege_reduction)))
        adjusted["customers_served"] = adjusted["total_arrivals"] - adjusted["customers_lost"]
    elif strategy_multiplier > 1.0:
        # Worse wait time = more lost customers
        renege_increase = (strategy_multiplier - 1.0) * 0.2  # Up to 20% increase in reneging
        adjusted["customers_lost"] = min(
            adjusted["total_arrivals"],
            int(adjusted["customers_lost"] * (1 + renege_increase))
        )
        adjusted["customers_served"] = adjusted["total_arrivals"] - adjusted["customers_lost"]
    
    # Recalculate throughput
    adjusted["throughput"] = (adjusted["customers_served"] / adjusted.get("duration", 480)) * 60
    
    return adjusted


def calculate_mm_c_queue(
    arrival_rate: float,
    num_tables: int,
    num_servers: int,
    avg_service_time: float,
    duration: int,
    reneg_threshold: int = 30,
    queue_strategy: str = "fcfs",
    party_size_distribution: Dict[str, float] = None,
) -> Dict[str, Any]:
    """
    Calculate queue metrics using M/M/c queueing theory.
    
    Uses:
    - Erlang C formula for queue length
    - Little's Law for wait times
    - Utilization factor (rho) for resource usage
    - Queue strategy adjustments
    
    Args:
        arrival_rate: Customers per hour
        num_tables: Number of tables
        num_servers: Number of servers
        avg_service_time: Average service time in minutes
        duration: Simulation duration in minutes
        reneg_threshold: Maximum wait time before customers leave (minutes)
        queue_strategy: Queue management strategy (fcfs, priority_small, priority_large, dynamic)
        party_size_distribution: Party size distribution for strategy adjustments
    
    Returns:
        Dictionary with calculated metrics
    """
    # Convert to per-minute rates
    lambda_rate = arrival_rate / 60.0  # arrivals per minute
    mu = 1.0 / avg_service_time  # service rate per server (per minute)
    c = min(num_servers, num_tables)  # effective number of servers
    
    # Utilization factor
    rho = lambda_rate / (c * mu) if c * mu > 0 else 1.0
    
    # Calculate P0 (probability of zero customers in system) using Erlang C
    if rho >= 1.0:
        # System is unstable (overloaded)
        P0 = 0.01
        Lq = lambda_rate * avg_service_time * 2  # Approximation for overloaded system
    else:
        # Calculate sum term for P0
        sum_term = 0.0
        for n in range(c):
            sum_term += (c * rho) ** n / factorial(n)
        
        # Last term in the series
        last_term = ((c * rho) ** c) / (factorial(c) * (1 - rho))
        P0 = 1.0 / (sum_term + last_term)
        
        # Calculate Lq (average queue length) using Erlang C formula
        Lq = (P0 * (c * rho) ** c * rho) / (factorial(c) * (1 - rho) ** 2)
    
    # Calculate wait time using Little's Law: Wq = Lq / lambda
    Wq = Lq / lambda_rate if lambda_rate > 0 else 0
    avg_wait_time = max(0, Wq)
    max_wait_time = avg_wait_time * 2.5 + random.uniform(0, 5)
    
    # Calculate customer metrics
    total_arrivals = int(lambda_rate * duration)
    # Customers lost due to reneging (leaving queue)
    renege_rate = min(0.3, avg_wait_time / reneg_threshold) if reneg_threshold > 0 else 0
    customers_served = int(total_arrivals * (1 - renege_rate))
    customers_lost = total_arrivals - customers_served
    
    # Calculate throughput (customers per hour)
    throughput = (customers_served / duration) * 60 if duration > 0 else 0
    
    # Calculate utilization metrics
    table_utilization = min(0.95, rho * 0.85)
    server_utilization = min(0.95, rho)
    peak_table_utilization = min(0.98, table_utilization * 1.1)
    peak_server_utilization = min(0.98, server_utilization * 1.1)
    
    # Base metrics dictionary
    base_metrics = {
        "avg_wait_time": round(avg_wait_time, 2),
        "max_wait_time": round(max_wait_time, 2),
        "Lq": round(Lq, 2),
        "rho": round(rho, 4),
        "customers_served": customers_served,
        "customers_lost": customers_lost,
        "total_arrivals": total_arrivals,
        "throughput": round(throughput, 2),
        "table_utilization": round(table_utilization, 4),
        "server_utilization": round(server_utilization, 4),
        "peak_table_utilization": round(peak_table_utilization, 4),
        "peak_server_utilization": round(peak_server_utilization, 4),
        "duration": duration,
    }
    
    # Apply queue strategy adjustments
    if party_size_distribution is None:
        party_size_distribution = {}
    
    adjusted_metrics = apply_queue_strategy(
        base_metrics,
        queue_strategy,
        party_size_distribution,
        avg_service_time
    )
    
    # Generate time series data (queue length over time)
    queue_length_stats = []
    time_series_data = []
    
    # Use adjusted metrics for time series
    adjusted_Lq = adjusted_metrics["Lq"]
    adjusted_wait_time = adjusted_metrics["avg_wait_time"]
    adjusted_table_util = adjusted_metrics["table_utilization"]
    
    for t in range(0, duration + 1, 5):
        progress = t / duration if duration > 0 else 0
        # Add sinusoidal variation to simulate real-world fluctuations
        time_noise = 1 + 0.2 * math.sin(progress * math.pi * 2)
        peak_factor = 1.2 if 20 < t < duration - 20 else 0.9
        
        queue_length = max(0, int(adjusted_Lq * time_noise * peak_factor))
        wait_time = max(0, adjusted_wait_time * time_noise * peak_factor)
        utilization = min(100, adjusted_table_util * 100 * time_noise)
        customers_in_system = int(adjusted_Lq + c * adjusted_metrics["rho"] * time_noise)
        
        if t % 60 == 0 and t > 0:
            queue_length_stats.append({
                "time": t,
                "queue_length": queue_length
            })
        
        time_series_data.append({
            "time": t,
            "waitTime": round(wait_time, 1),
            "queueLength": queue_length,
            "utilization": round(utilization, 1),
            "customersInSystem": customers_in_system,
        })
    
    # Add time series data to adjusted metrics
    adjusted_metrics["queue_length_stats"] = queue_length_stats
    adjusted_metrics["time_series_data"] = time_series_data
    
    return adjusted_metrics


def run_simulation(config: dict) -> Tuple[dict, dict]:
    """
    Run queue optimization simulation using M/M/c queueing theory.
    
    Implements:
    - M/M/c queue model (Poisson arrivals, exponential service, c servers)
    - Erlang C formula for queue length calculation
    - Little's Law for wait time calculation
    - Utilization metrics for tables and servers
    - Party size distribution with weighted service times
    - Queue management strategies (FCFS, priority, dynamic)
    
    Returns:
        (results_json, metadata_json)
    """
    start_time = datetime.utcnow()
    start_ms = time.time()
    
    # Extract configuration parameters
    arrival_rate = config.get("arrival_rate", 20.0)  # customers per hour
    num_tables = config.get("num_tables", 20)
    num_servers = config.get("num_servers", 5)
    duration = config.get("duration", 480)  # minutes (8 hours default)
    reneg_threshold = config.get("reneg_threshold", 30)  # minutes
    queue_strategy = config.get("queue_strategy", "fcfs")
    party_size_distribution = config.get("party_size_distribution", {})
    service_time_params = config.get("service_time_params", {})
    
    # Calculate weighted average service time based on party size distribution
    avg_service_time = calculate_weighted_service_time(
        party_size_distribution,
        service_time_params
    )
    
    # Run M/M/c queue calculations with strategy
    metrics = calculate_mm_c_queue(
        arrival_rate=arrival_rate,
        num_tables=num_tables,
        num_servers=num_servers,
        avg_service_time=avg_service_time,
        duration=duration,
        reneg_threshold=reneg_threshold,
        queue_strategy=queue_strategy,
        party_size_distribution=party_size_distribution,
    )
    
    # Calculate average dining time (weighted by party size distribution)
    # This represents the actual average service time considering party sizes
    avg_dining_time = avg_service_time
    
    # Build results structure matching expected format
    results = {
        "performance_metrics": {
            "avg_waiting_time": metrics["avg_wait_time"],
            "max_waiting_time": metrics["max_wait_time"],
            "median_waiting_time": round(metrics["avg_wait_time"] * 0.9, 2),
            "avg_dining_time": round(avg_dining_time, 2),
            "median_dining_time": round(avg_dining_time * 0.95, 2),
            "throughput": metrics["throughput"],
        },
        "utilization_metrics": {
            "table_utilization": round(metrics["table_utilization"] * 100, 2),
            "server_utilization": round(metrics["server_utilization"] * 100, 2),
            "peak_table_utilization": round(metrics["peak_table_utilization"] * 100, 2),
            "peak_server_utilization": round(metrics["peak_server_utilization"] * 100, 2),
            "peak_load": int(metrics["total_arrivals"] * 0.15),  # Approximate peak
        },
        "queue_metrics": {
            "queue_length_avg": metrics["Lq"],
            "queue_length_max": round(metrics["Lq"] * 2.5, 2),
        },
        "customer_metrics": {
            "customers_served": metrics["customers_served"],
            "customers_lost": metrics["customers_lost"],
            "total_customers_arrived": metrics["total_arrivals"],
        },
        "queue_length_stats": metrics["queue_length_stats"],
        "time_series_data": metrics["time_series_data"],
        "service_distribution": {
            "party_size_distribution": party_size_distribution,
            "service_time_params": service_time_params,
        },
    }
    
    execution_time_ms = int((time.time() - start_ms) * 1000)
    
    metadata = {
        "execution_time_ms": execution_time_ms,
        "simulation_start_time": start_time.isoformat() + "Z",
        "simulation_end_time": datetime.utcnow().isoformat() + "Z",
        "random_seed": None,
        "version": "1.0.0",
        "algorithm": "M/M/c Queueing Theory",
        "queue_strategy": queue_strategy,
        "weighted_service_time": round(avg_service_time, 2),
    }
    
    return results, metadata
