import time
import numpy as np
from core.pipeline import RiskPipeline
from stream.generator import TransactionStreamGenerator

def run_benchmark(num_transactions: int = 1000):
    print(f"Running latency & throughput benchmark across {num_transactions:,} transactions...")
    pipeline = RiskPipeline()
    generator = TransactionStreamGenerator(num_users=200)
    
    latencies = []
    start_total = time.perf_counter()
    
    for _ in range(num_transactions):
        tx = generator.generate_single_transaction()
        res = pipeline.process_transaction(tx)
        latencies.append(res.latencies["total_ms"])
        
    total_elapsed = time.perf_counter() - start_total
    tps = num_transactions / total_elapsed
    
    avg_lat = np.mean(latencies)
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    
    print("\n" + "=" * 55)
    print("⚡ BENCHMARK PERFORMANCE RESULTS")
    print("=" * 55)
    print(f"Total Transactions Processed : {num_transactions:,}")
    print(f"Total Time Elapsed          : {total_elapsed:.3f} s")
    print(f"Throughput (TPS)            : {tps:,.1f} transactions/sec")
    print(f"Average Pipeline Latency    : {avg_lat:.3f} ms")
    print(f"50th Percentile (p50)       : {p50:.3f} ms")
    print(f"95th Percentile (p95)       : {p95:.3f} ms")
    print(f"99th Percentile (p99)       : {p99:.3f} ms")
    print("=" * 55)
    assert avg_lat < 10.0, f"Average latency {avg_lat:.2f}ms exceeds SLA target of 10ms!"
    print("✅ SLA Target Met (< 10ms average latency)!")

if __name__ == "__main__":
    run_benchmark(1000)
