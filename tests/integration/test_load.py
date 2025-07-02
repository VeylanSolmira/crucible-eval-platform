#!/usr/bin/env python3
"""
Load testing for concurrent evaluations.

Tests the platform's ability to handle multiple concurrent evaluations
and measures performance metrics.
"""

import json
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

API_BASE_URL = "http://localhost:8000/api"


class LoadTestResult:
    """Track results from a single evaluation submission."""

    def __init__(self):
        self.eval_id: str = ""
        self.submit_time: float = 0.0
        self.complete_time: float = 0.0
        self.total_duration: float = 0.0
        self.status: str = ""
        self.error: str = ""


def submit_and_track_evaluation(index: int, code: str) -> LoadTestResult:
    """Submit an evaluation and track its completion."""
    result = LoadTestResult()

    try:
        # Submit evaluation
        start_time = time.time()
        eval_request = {"code": code, "language": "python", "engine": "docker", "timeout": 60}

        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        response.raise_for_status()
        result.eval_id = response.json()["eval_id"]
        result.submit_time = time.time() - start_time

        # Poll for completion
        max_polls = 120  # 2 minutes max
        poll_interval = 0.5

        for _ in range(max_polls):
            response = requests.get(f"{API_BASE_URL}/eval/{result.eval_id}", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                result.status = status_data.get("status", "unknown")

                if result.status in ["completed", "failed"]:
                    result.complete_time = time.time() - start_time
                    result.total_duration = result.complete_time
                    break

            time.sleep(poll_interval)

        if result.status not in ["completed", "failed"]:
            result.error = "Timeout waiting for completion"
            result.status = "timeout"

    except Exception as e:
        result.error = str(e)
        result.status = "error"
        result.total_duration = time.time() - start_time

    return result


def run_load_test(concurrent_count: int, total_evaluations: int):
    """Run load test with specified concurrency."""
    print(f"\n{'=' * 60}")
    print(f"LOAD TEST: {concurrent_count} concurrent, {total_evaluations} total")
    print(f"{'=' * 60}\n")

    # Generate test codes
    test_codes = []
    for i in range(total_evaluations):
        # Mix of fast and slow evaluations
        if i % 3 == 0:
            # Fast
            code = f"print('Fast eval {i}')"
        elif i % 3 == 1:
            # Medium
            code = f"import time\nprint('Medium eval {i}')\ntime.sleep(1)"
        else:
            # Slow
            code = f"import time\nprint('Slow eval {i}')\nfor i in range(3):\n    time.sleep(0.5)\n    print(f'Step {{i}}')"

        test_codes.append(code)

    # Run evaluations
    results: List[LoadTestResult] = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(submit_and_track_evaluation, i, code): i
            for i, code in enumerate(test_codes)
        }

        # Track progress
        completed = 0
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)
            completed += 1

            # Progress update every 10 completions
            if completed % 10 == 0:
                print(f"Progress: {completed}/{total_evaluations} completed")

    total_time = time.time() - start_time

    # Analyze results
    successful = [r for r in results if r.status == "completed"]
    failed = [r for r in results if r.status == "failed"]
    errors = [r for r in results if r.status in ["error", "timeout"]]

    # Calculate metrics
    if successful:
        submit_times = [r.submit_time for r in successful]
        complete_times = [r.total_duration for r in successful]

        metrics = {
            "total_evaluations": total_evaluations,
            "concurrent_count": concurrent_count,
            "total_time": total_time,
            "successful": len(successful),
            "failed": len(failed),
            "errors": len(errors),
            "throughput": len(successful) / total_time,
            "submit_time": {
                "min": min(submit_times),
                "max": max(submit_times),
                "avg": statistics.mean(submit_times),
                "median": statistics.median(submit_times),
            },
            "complete_time": {
                "min": min(complete_times),
                "max": max(complete_times),
                "avg": statistics.mean(complete_times),
                "median": statistics.median(complete_times),
            },
        }
    else:
        metrics = {
            "total_evaluations": total_evaluations,
            "concurrent_count": concurrent_count,
            "total_time": total_time,
            "successful": 0,
            "failed": len(failed),
            "errors": len(errors),
            "throughput": 0,
        }

    # Print summary
    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Successful: {metrics['successful']}/{total_evaluations}")
    print(f"Failed: {metrics['failed']}")
    print(f"Errors: {metrics['errors']}")
    print(f"Throughput: {metrics['throughput']:.2f} evals/second")

    if successful:
        print("\nSubmission Times:")
        print(f"  Min: {metrics['submit_time']['min']:.3f}s")
        print(f"  Max: {metrics['submit_time']['max']:.3f}s")
        print(f"  Avg: {metrics['submit_time']['avg']:.3f}s")
        print(f"  Median: {metrics['submit_time']['median']:.3f}s")

        print("\nCompletion Times:")
        print(f"  Min: {metrics['complete_time']['min']:.3f}s")
        print(f"  Max: {metrics['complete_time']['max']:.3f}s")
        print(f"  Avg: {metrics['complete_time']['avg']:.3f}s")
        print(f"  Median: {metrics['complete_time']['median']:.3f}s")

    # Save detailed results
    detailed_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics,
        "evaluations": [
            {
                "eval_id": r.eval_id,
                "status": r.status,
                "submit_time": r.submit_time,
                "total_duration": r.total_duration,
                "error": r.error,
            }
            for r in results
        ],
    }

    filename = f"load_test_results_{concurrent_count}x{total_evaluations}.json"
    with open(filename, "w") as f:
        json.dump(detailed_results, f, indent=2)

    print(f"\nDetailed results saved to {filename}")

    return metrics


def run_progressive_load_test():
    """Run load tests with increasing concurrency."""
    print("=" * 60)
    print("PROGRESSIVE LOAD TEST")
    print("=" * 60)

    test_configurations = [
        (5, 10),  # 5 concurrent, 10 total
        (10, 20),  # 10 concurrent, 20 total
        (20, 40),  # 20 concurrent, 40 total
        (50, 100),  # 50 concurrent, 100 total
    ]

    all_results = []

    for concurrent, total in test_configurations:
        metrics = run_load_test(concurrent, total)
        all_results.append(metrics)

        # Brief pause between tests
        print("\nPausing 5 seconds before next test...")
        time.sleep(5)

    # Save consolidated results
    with open("progressive_load_test_results.json", "w") as f:
        json.dump(
            {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "tests": all_results}, f, indent=2
        )

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "progressive":
        run_progressive_load_test()
    else:
        # Default: single load test
        concurrent = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        total = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        run_load_test(concurrent, total)
