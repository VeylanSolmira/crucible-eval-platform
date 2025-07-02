#!/usr/bin/env python3
"""Async/await example - demonstrates asynchronous programming"""

import asyncio
import time


async def fetch_data(url, delay):
    """Simulate async data fetching"""
    print(f"Starting fetch from {url}")
    await asyncio.sleep(delay)  # Simulate network delay
    print(f"Completed fetch from {url} after {delay}s")
    return f"Data from {url}"


async def process_data(data):
    """Simulate async data processing"""
    print(f"Processing: {data}")
    await asyncio.sleep(0.5)  # Simulate processing time
    return f"Processed {data}"


async def main():
    print("Async Programming Example")
    print("=" * 30)

    # Sequential execution
    print("\n1. Sequential execution:")
    start = time.time()

    data1 = await fetch_data("api.example.com/users", 1)
    data2 = await fetch_data("api.example.com/posts", 1)

    result1 = await process_data(data1)
    result2 = await process_data(data2)

    print(f"Sequential time: {time.time() - start:.2f}s")

    # Concurrent execution
    print("\n2. Concurrent execution:")
    start = time.time()

    # Fetch concurrently
    data1, data2 = await asyncio.gather(
        fetch_data("api.example.com/users", 1), fetch_data("api.example.com/posts", 1)
    )

    # Process concurrently
    result1, result2 = await asyncio.gather(process_data(data1), process_data(data2))

    print(f"Concurrent time: {time.time() - start:.2f}s")

    # Multiple concurrent tasks
    print("\n3. Multiple tasks:")
    urls = [f"api.example.com/data{i}" for i in range(5)]
    tasks = [fetch_data(url, 0.5) for url in urls]

    results = await asyncio.gather(*tasks)
    print(f"Fetched {len(results)} results concurrently")


if __name__ == "__main__":
    # Note: asyncio.run() might not be available in all Python environments
    # Fall back to older style if needed
    try:
        asyncio.run(main())
    except AttributeError:
        # Python < 3.7
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
