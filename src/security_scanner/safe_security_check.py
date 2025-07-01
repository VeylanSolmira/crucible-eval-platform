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
    results = {
        'timestamp': datetime.now().isoformat(),
        'environment': {},
        'security_features': {}
    }
    
    # Check if we're in a container
    in_container = False
    container_type = 'none'
    
    # Docker check
    if os.path.exists('/.dockerenv'):
        in_container = True
        container_type = 'docker'
    
    # Check cgroup (safe read-only)
    try:
        with open('/proc/self/cgroup', 'r') as f:
            cgroup_content = f.read()
            if 'docker' in cgroup_content:
                in_container = True
                container_type = 'docker'
            elif 'containerd' in cgroup_content:
                in_container = True
                container_type = 'containerd'
    except:
        pass
    
    results['environment']['in_container'] = in_container
    results['environment']['container_type'] = container_type
    results['environment']['hostname'] = os.environ.get('HOSTNAME', 'unknown')
    results['environment']['user'] = f"{os.getuid()}:{os.getgid()}"
    
    # Check security features (all read-only)
    security_checks = {
        'running_as_root': os.getuid() == 0,
        'can_read_docker_socket': os.path.exists('/var/run/docker.sock'),
        'can_read_proc_1': os.path.exists('/proc/1/environ'),
        'has_network': check_network_safely(),
        'filesystem_writable': check_filesystem_safely(),
        'resource_limits': check_limits_safely()
    }
    
    results['security_features'] = security_checks
    
    return results


def check_network_safely():
    """Check network availability without making connections"""
    try:
        # Just check if we have network interfaces
        result = subprocess.run(['ip', 'link', 'show'], 
                              capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            # Count interfaces (lo, eth0, etc)
            interfaces = len([l for l in result.stdout.split('\n') 
                            if ': ' in l and not l.startswith(' ')])
            return f"{interfaces} interfaces"
        return "unknown"
    except:
        return "no ip command"


def check_filesystem_safely():
    """Check filesystem permissions without writing"""
    checks = []
    
    # Check if key paths are writable (doesn't actually write)
    test_paths = ['/etc', '/root', '/var', '/tmp']
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
        mem_limit = "unlimited" if hard == resource.RLIM_INFINITY else f"{hard/(1024*1024):.0f}MB"
        
        # Process limit  
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        proc_limit = "unlimited" if hard == resource.RLIM_INFINITY else str(hard)
        
        return f"memory:{mem_limit}, processes:{proc_limit}"
    except:
        return "cannot read limits"


def generate_report(results):
    """Generate a safe security report"""
    report = f"""# Safe Security Environment Check

Generated: {results['timestamp']}

## Environment
- Container: {'Yes (' + results['environment']['container_type'] + ')' if results['environment']['in_container'] else 'No'}
- User: {results['environment']['user']} {'(ROOT!)' if results['security_features']['running_as_root'] else '(non-root)'}
- Hostname: {results['environment']['hostname']}

## Security Features
"""
    
    for feature, value in results['security_features'].items():
        if feature == 'running_as_root':
            status = '❌ UNSAFE' if value else '✅ Safe'
        elif feature == 'can_read_docker_socket':
            status = '❌ UNSAFE' if value else '✅ Safe'
        elif feature == 'can_read_proc_1':
            status = '⚠️  Partial isolation' if value else '✅ Isolated'
        else:
            status = str(value)
        
        report += f"- {feature.replace('_', ' ').title()}: {status}\n"
    
    report += """
## Summary

"""
    
    if results['environment']['in_container']:
        report += "Running in a container provides some isolation, but:\n"
        if results['environment']['container_type'] == 'docker':
            report += "- Docker alone is not sufficient for untrusted code\n"
            report += "- Consider adding: --read-only, --cap-drop ALL, --security-opt no-new-privileges\n"
            report += "- For AI evaluation, use gVisor (runsc) runtime for kernel-level protection\n"
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
    print(f"\nEnvironment: {'Container (' + results['environment']['container_type'] + ')' if results['environment']['in_container'] else 'Host system'}")
    print(f"User: {results['environment']['user']}")
    
    # Save results
    with open('safe_security_check.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    report = generate_report(results)
    with open('SAFE_SECURITY_CHECK.md', 'w') as f:
        f.write(report)
    
    print("\n✅ Check complete!")
    print("📄 Report saved to: SAFE_SECURITY_CHECK.md")
    print("📊 Data saved to: safe_security_check.json")


if __name__ == '__main__':
    main()