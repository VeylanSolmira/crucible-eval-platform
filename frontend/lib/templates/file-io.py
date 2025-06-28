#!/usr/bin/env python3
"""File I/O example - demonstrates file operations"""

def write_file(filename, content):
    """Write content to a file"""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Wrote {len(content)} characters to {filename}")

def read_file(filename):
    """Read and display file content"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        print(f"Read {len(content)} characters from {filename}")
        return content
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None

def main():
    # Write a test file
    test_content = "This is a test file.\nIt has multiple lines.\nFile I/O works!"
    write_file('/tmp/test.txt', test_content)
    
    # Read it back
    content = read_file('/tmp/test.txt')
    if content:
        print("\nFile content:")
        print(content)
    
    # Try reading non-existent file
    read_file('/tmp/nonexistent.txt')

if __name__ == "__main__":
    main()