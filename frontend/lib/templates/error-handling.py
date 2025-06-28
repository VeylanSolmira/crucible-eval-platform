#!/usr/bin/env python3
"""Error handling example - demonstrates various exception scenarios"""

def divide_numbers(a, b):
    """Division with error handling"""
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        print(f"Error: Cannot divide {a} by zero!")
        return None
    except TypeError as e:
        print(f"Type error: {e}")
        return None

def parse_integer(value):
    """Parse integer with error handling"""
    try:
        return int(value)
    except ValueError:
        print(f"Error: '{value}' is not a valid integer")
        return None

def access_list(lst, index):
    """Safe list access"""
    try:
        return lst[index]
    except IndexError:
        print(f"Error: Index {index} is out of range (list has {len(lst)} items)")
        return None

def main():
    print("Error Handling Examples")
    print("=" * 30)
    
    # Division errors
    print("\n1. Division:")
    print(f"10 / 2 = {divide_numbers(10, 2)}")
    print(f"10 / 0 = {divide_numbers(10, 0)}")
    print(f"'10' / 2 = {divide_numbers('10', 2)}")
    
    # Parsing errors
    print("\n2. Integer parsing:")
    for value in ["42", "3.14", "abc", ""]:
        result = parse_integer(value)
        print(f"parse_integer('{value}') = {result}")
    
    # Index errors
    print("\n3. List access:")
    my_list = [10, 20, 30]
    for index in [0, 2, 5, -1]:
        result = access_list(my_list, index)
        print(f"my_list[{index}] = {result}")
    
    # Raise custom exception
    print("\n4. Custom exception:")
    try:
        raise RuntimeError("This is a deliberate error for testing!")
    except RuntimeError as e:
        print(f"Caught RuntimeError: {e}")

if __name__ == "__main__":
    main()