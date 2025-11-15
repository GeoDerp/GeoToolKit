# Test Python file with potential security issue
import subprocess
import os

def run_command(user_input):
    # This is intentionally vulnerable code for testing
    command = f"echo {user_input}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def read_file(filename):
    # Another potential issue - no path validation
    with open(filename, 'r') as f:
        return f.read()

if __name__ == "__main__":
    user_data = input("Enter command: ")
    output = run_command(user_data)
    print(f"Output: {output}")