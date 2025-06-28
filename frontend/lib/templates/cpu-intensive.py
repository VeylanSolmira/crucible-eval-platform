#!/usr/bin/env python3
"""CPU-intensive computation example - prime number calculation"""

import time
import math

def is_prime(n):
    """Check if a number is prime"""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def find_primes(limit):
    """Find all prime numbers up to limit"""
    primes = []
    for n in range(2, limit + 1):
        if is_prime(n):
            primes.append(n)
    return primes

def main():
    print("Prime Number Calculator")
    print("=" * 30)
    
    # Test with different limits to see performance
    limits = [100, 1000, 10000]
    
    for limit in limits:
        start_time = time.time()
        primes = find_primes(limit)
        elapsed = time.time() - start_time
        
        print(f"\nPrimes up to {limit}:")
        print(f"  Found: {len(primes)} primes")
        print(f"  Time: {elapsed:.3f} seconds")
        print(f"  Last 5: {primes[-5:]}")
    
    # Memory usage test
    print("\n" + "=" * 30)
    print("Testing memory usage...")
    big_list = [i for i in range(1000000)]
    print(f"Created list with {len(big_list)} elements")

if __name__ == "__main__":
    main()