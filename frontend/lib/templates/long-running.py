#!/usr/bin/env python3
"""Long-running process example - for testing task management and monitoring"""

import time
import sys

def simulate_work(iteration):
    """Simulate some computational work"""
    # Do some actual work to use CPU
    result = sum(i * i for i in range(10000))
    return result

def main():
    print("Starting long-running process...")
    print("This will run for 30 iterations with 1 second delay between each")
    print("-" * 50)
    
    total_iterations = 30
    start_time = time.time()
    
    try:
        for i in range(total_iterations):
            # Print status with timestamp
            current_time = time.time() - start_time
            print(f"[{current_time:6.2f}s] Iteration {i + 1}/{total_iterations} - Working...", flush=True)
            
            # Simulate some work
            result = simulate_work(i)
            
            # Print completion of work
            print(f"[{current_time:6.2f}s] Iteration {i + 1}/{total_iterations} - Completed (result: {result})", flush=True)
            
            # Progress indicator every 5 iterations
            if (i + 1) % 5 == 0:
                progress = ((i + 1) / total_iterations) * 100
                print(f"\n>>> Progress: {progress:.1f}% complete <<<\n", flush=True)
            
            # Sleep to simulate time between operations
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n!!! Process interrupted by user !!!")
        elapsed = time.time() - start_time
        print(f"Ran for {elapsed:.2f} seconds, completed {i} iterations")
        sys.exit(1)
    
    # Final summary
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("Process completed successfully!")
    print(f"Total iterations: {total_iterations}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per iteration: {total_time/total_iterations:.2f} seconds")

if __name__ == "__main__":
    main()