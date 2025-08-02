import time
import sys

print("Starting 15-second test evaluation", flush=True)
print(f"Process ID: {sys.argv[0]}", flush=True)

for i in range(15):
    print(f"Second {i+1}/15: Still running...", flush=True)
    time.sleep(1)
    
    if i == 5:
        print("WARNING: Halfway point reached!", flush=True)
    
    if i == 10:
        print("ERROR: Approaching critical failure!", flush=True)

print("About to throw exception!", flush=True)
raise RuntimeError("BOOM! This is the intentional exception after 15 seconds")