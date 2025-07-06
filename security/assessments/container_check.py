#!/usr/bin/env python3
"""
Safe Security Check - Shows container isolation without attacks
This script is 100% safe to run anywhere
"""

import os
import subprocess
import json
from datetime import datetime


def check_environment():
    """Perform safe environment checks"""
    results = {"timestamp": datetime.now().isoformat(), "environment": {}, "security_features": {}}

    # Check if we're in a container
    in_container = False
    container_type = "none"

    # Docker check
    if os.path.exists("/.dockerenv"):
        in_container = True
        container_type = "docker"

    # Check cgroup (safe read-only)
    try:
        with open("/proc/self/cgroup", "r") as f:
            cgroup_content = f.read()
            if "docker" in cgroup_content:
                in_container = True
                container_type = "docker"
            elif "containerd" in cgroup_content:
                in_container = True
                container_type = "containerd"
    except (FileNotFoundError, IOError):
        pass  # Not in container or can't read cgroup

    results["environment"]["in_container"] = in_container
    results["environment"]["container_type"] = container_type
    results["environment"]["hostname"] = os.environ.get("HOSTNAME", "unknown")
    results["environment"]["user"] = f"{os.getuid()}:{os.getgid()}"

    # Check security features (all read-only)
    security_checks = {
        "running_as_root": os.getuid() == 0,
        "can_read_docker_socket": os.path.exists("/var/run/docker.sock"),
        "can_read_proc_1": os.path.exists("/proc/1/environ"),
        "has_network": check_network_safely(),
        "filesystem_writable": check_filesystem_safely(),
        "resource_limits": check_limits_safely(),
    }

    results["security_features"] = security_checks

    return results


def check_network_safely():
    """Check network availability without making connections"""
    try:
        # Just check if we have network interfaces
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            # Count interfaces (lo, eth0, etc)
            interfaces = len(
                [
                    line
                    for line in result.stdout.split("\n")
                    if ": " in line and not line.startswith(" ")
                ]
            )
            return f"{interfaces} interfaces"
        return "unknown"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "no ip command"


def check_filesystem_safely():
    """Check filesystem permissions without writing"""
    checks = []

    # Check if key paths are writable (doesn't actually write)
    test_paths = ["/etc", "/root", "/var", "/tmp"]
    for path in test_paths:
        if os.path.exists(path) and os.access(path, os.W_OK):
            checks.append(f"{path}:writable")
        else:
            checks.append(f"{path}:readonly")

    return ", ".join(checks)


def check_limits_safely():
    """Check resource limits without consuming resources"""
    try:
        import resource

        # Memory limit
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        mem_limit = (
            "unlimited" if hard == resource.RLIM_INFINITY else f"{hard / (1024 * 1024):.0f}MB"
        )

        # Process limit
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        proc_limit = "unlimited" if hard == resource.RLIM_INFINITY else str(hard)

        return f"memory:{mem_limit}, processes:{proc_limit}"
    except (OSError, ValueError):
        return "cannot read limits"


def generate_report(results):
    """Generate a safe security report"""
    report = f"""# Safe Security Environment Check

Generated: {results["timestamp"]}

## Environment
- Container: {"Yes (" + results["environment"]["container_type"] + ")" if results["environment"]["in_container"] else "No"}
- User: {results["environment"]["user"]} {"(ROOT!)" if results["security_features"]["running_as_root"] else "(non-root)"}
- Hostname: {results["environment"]["hostname"]}

## Security Features
"""

    for feature, value in results["security_features"].items():
        if feature == "running_as_root":
            status = "❌ UNSAFE" if value else "✅ Safe"
        elif feature == "can_read_docker_socket":
            status = "❌ UNSAFE" if value else "✅ Safe"
        elif feature == "can_read_proc_1":
            status = "⚠️  Partial isolation" if value else "✅ Isolated"
        else:
            status = str(value)

        report += f"- {feature.replace('_', ' ').title()}: {status}\n"

    report += """
## Summary

"""

    if results["environment"]["in_container"]:
        report += "Running in a container provides some isolation, but:\n"
        if results["environment"]["container_type"] == "docker":
            report += "- Docker alone is not sufficient for untrusted code\n"
            report += (
                "- Consider adding: --read-only, --cap-drop ALL, --security-opt no-new-privileges\n"
            )
            report += (
                "- For AI evaluation, use gVisor (runsc) runtime for kernel-level protection\n"
            )
    else:
        report += "⚠️  NOT running in a container - no isolation!\n"
        report += "Never run untrusted AI code without proper sandboxing.\n"

    return report


def main():
    print("🔒 Safe Security Environment Check")
    print("This performs read-only checks - safe to run anywhere")
    print("-" * 50)

    results = check_environment()

    # Print summary
    print(
        f"\nEnvironment: {'Container (' + results['environment']['container_type'] + ')' if results['environment']['in_container'] else 'Host system'}"
    )
    print(f"User: {results['environment']['user']}")

    # Determine output directory with fallbacks
    output_dir = os.environ.get("SECURITY_CHECK_OUTPUT_DIR", "")
    
    if not output_dir:
        # Try various locations in order of preference
        possible_dirs = [
            ".",  # Current directory
            "/tmp",  # Temp directory (usually writable in containers)
            "/var/tmp",  # Alternative temp
            os.environ.get("HOME", ""),  # User home
        ]
        
        # If we're outside a container, also try tests/output
        if not results["environment"]["in_container"]:
            possible_dirs.insert(0, "tests/output")
            possible_dirs.insert(1, "../tests/output")
            possible_dirs.insert(2, "../../tests/output")
        
        for dir_path in possible_dirs:
            if dir_path and os.path.exists(dir_path) and os.access(dir_path, os.W_OK):
                output_dir = dir_path
                break
    
    # Try to save results
    files_saved = []
    
    if output_dir:
        try:
            json_path = os.path.join(output_dir, "safe_security_check.json")
            with open(json_path, "w") as f:
                json.dump(results, f, indent=2)
            files_saved.append(f"📊 Data saved to: {json_path}")
        except (IOError, OSError) as e:
            print(f"⚠️  Could not save JSON file: {e}")
    
    report = generate_report(results)
    
    if output_dir:
        try:
            md_path = os.path.join(output_dir, "SAFE_SECURITY_CHECK.md")
            with open(md_path, "w") as f:
                f.write(report)
            files_saved.append(f"📄 Report saved to: {md_path}")
        except (IOError, OSError) as e:
            print(f"⚠️  Could not save Markdown file: {e}")
    
    print("\n✅ Check complete!")
    
    if files_saved:
        for msg in files_saved:
            print(msg)
    else:
        print("⚠️  Could not save files (no writable directory found)")
        print("\n" + "="*50)
        print("REPORT OUTPUT:")
        print("="*50)
        print(report)
        print("\n" + "="*50)
        print("JSON OUTPUT:")
        print("="*50)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
