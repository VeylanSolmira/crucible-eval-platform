"""
Robust gVisor detection for tests.
"""

def is_running_under_gvisor():
    """
    Detect if running under gVisor by checking multiple indicators.
    Returns: (is_gvisor: bool, detection_method: str)
    """
    import os
    
    # Method 1: Check if key /proc files are missing (strong indicator)
    gvisor_blocked_files = ['/proc/kcore', '/proc/kallsyms', '/proc/modules']
    missing_count = 0
    for path in gvisor_blocked_files:
        if not os.path.exists(path):
            missing_count += 1
    
    if missing_count == len(gvisor_blocked_files):
        return True, f"Missing all gVisor-blocked files: {', '.join(gvisor_blocked_files)}"
    
    # Method 2: Check kernel version for known gVisor patterns
    try:
        with open('/proc/version', 'r') as f:
            kernel = f.read().strip()
            # Known gVisor kernel versions
            if 'gVisor' in kernel:
                return True, "Kernel version contains 'gVisor'"
            if 'Linux version 4.4.0 #1 SMP Sun Jan 10 15:06:54 PST 2016' in kernel:
                return True, "Kernel version matches known gVisor pattern (4.4.0)"
    except:
        pass
    
    # Method 3: Check if unshare syscall is blocked
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        CLONE_NEWNS = 0x00020000
        result = libc.unshare(CLONE_NEWNS)
        if result == -1 and missing_count >= 2:
            # unshare blocked + most proc files missing = likely gVisor
            return True, "unshare() blocked and proc files missing"
    except:
        pass
    
    return False, "No gVisor indicators found"


if __name__ == "__main__":
    is_gvisor, method = is_running_under_gvisor()
    print(f"Running under gVisor: {is_gvisor}")
    print(f"Detection method: {method}")