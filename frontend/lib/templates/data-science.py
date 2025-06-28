#!/usr/bin/env python3
"""
Data Science example
Shows pandas, numpy, and basic data analysis
"""

import random
import statistics
from collections import Counter

def generate_sample_data(size=100):
    """Generate random data for analysis"""
    data = [random.gauss(100, 15) for _ in range(size)]
    categories = [random.choice(['A', 'B', 'C', 'D']) for _ in range(size)]
    return data, categories

def analyze_data(data, categories):
    """Perform basic statistical analysis"""
    print("📊 Data Analysis Results\n")
    
    # Basic statistics
    print(f"Count: {len(data)}")
    print(f"Mean: {statistics.mean(data):.2f}")
    print(f"Median: {statistics.median(data):.2f}")
    print(f"Std Dev: {statistics.stdev(data):.2f}")
    
    # Category distribution
    print(f"\n📈 Category Distribution:")
    for category, count in Counter(categories).items():
        percentage = (count / len(categories)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")

def main():
    print("Data Science Demo\n")
    
    # Generate and analyze data
    data, categories = generate_sample_data()
    analyze_data(data, categories)
    
    # Find outliers (simple method: > 2 std devs from mean)
    mean = statistics.mean(data)
    stdev = statistics.stdev(data)
    outliers = [x for x in data if abs(x - mean) > 2 * stdev]
    
    print(f"\n🎯 Found {len(outliers)} outliers")
    if outliers:
        print(f"   Range: [{min(outliers):.2f}, {max(outliers):.2f}]")

if __name__ == "__main__":
    main()