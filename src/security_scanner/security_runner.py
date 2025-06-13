"""
Security Scenario Runner
Executes attack scenarios against different execution engines to verify security
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any

import sys
import os
# Add parent directory to path for imports
# Import from platform components

from ..platform.components import SubprocessEngine, DockerEngine, GVisorEngine


class SecurityTestRunner:
    """Runs security attack scenarios and generates reports"""
    
    def __init__(self, scenarios: Dict[str, Any], include_subprocess: bool = False):
        """
        Initialize security test runner with explicit scenarios.
        
        Args:
            scenarios: Dictionary of scenarios to run (REQUIRED - no default for safety)
            include_subprocess: Whether to include subprocess engine (default: False)
        """
        if not scenarios:
            raise ValueError("Scenarios parameter is required and cannot be empty")
            
        self.scenarios = scenarios
        self.results = []
        self.engines = {}
        self._setup_engines(include_subprocess)
    
    def _setup_engines(self, include_subprocess=False):
        """Initialize available execution engines"""
        # Only include subprocess if explicitly requested (DANGEROUS!)
        if include_subprocess:
            print("⚠️  WARNING: Including subprocess engine - DO NOT RUN ATTACK SCENARIOS!")
            print("⚠️  Some attacks could affect your local system!")
            self.engines['subprocess'] = SubprocessEngine()
        else:
            print("✅ Skipping subprocess engine for safety")
        
        # Try to set up Docker
        try:
            self.engines['docker'] = DockerEngine()
            print("✅ Docker engine initialized")
        except Exception as e:
            print(f"⚠️  Docker not available: {e}")
        
        # Try to set up gVisor
        try:
            self.engines['gvisor'] = GVisorEngine()
            print("✅ gVisor engine initialized")
        except Exception as e:
            print(f"⚠️  gVisor not available: {e}")
    
    def run_scenario(self, scenario_id: str, scenario: Dict[str, Any], engine_name: str) -> Dict[str, Any]:
        """Run a single scenario on a specific engine"""
        engine = self.engines.get(engine_name)
        if not engine:
            return {
                'scenario_id': scenario_id,
                'engine': engine_name,
                'status': 'skipped',
                'reason': 'Engine not available'
            }
        
        print(f"  Testing {engine_name}...", end='', flush=True)
        
        start_time = time.time()
        try:
            result = engine.execute(scenario['code'], f"security-{scenario_id}-{engine_name}")
            duration = time.time() - start_time
            
            # Analyze output to determine if attack was blocked
            output = result.get('output', '')
            blocked_count = output.count('✅ PASS:')
            failed_count = output.count('❌ CRITICAL:') + output.count('❌ WARNING:')
            
            # Determine overall status
            if failed_count > 0:
                status = 'vulnerable'
                print(f" ❌ VULNERABLE ({failed_count} bypasses)")
            elif blocked_count > 0:
                status = 'secure'
                print(f" ✅ SECURE ({blocked_count} blocks)")
            else:
                status = 'unknown'
                print(f" ⚠️  UNKNOWN")
            
            return {
                'scenario_id': scenario_id,
                'scenario_name': scenario['name'],
                'engine': engine_name,
                'status': status,
                'blocked_count': blocked_count,
                'failed_count': failed_count,
                'duration': duration,
                'output': output,
                'threat_level': scenario['threat_level']
            }
            
        except Exception as e:
            print(f" ⚠️  ERROR: {str(e)}")
            return {
                'scenario_id': scenario_id,
                'scenario_name': scenario['name'],
                'engine': engine_name,
                'status': 'error',
                'error': str(e),
                'threat_level': scenario['threat_level']
            }
    
    def run_all_scenarios(self):
        """Run all attack scenarios against all engines"""
        print("\n🔒 CONTAINER SECURITY EVALUATION")
        print("=" * 60)
        print(f"Testing {len(self.scenarios)} attack scenarios")
        print(f"Engines available: {list(self.engines.keys())}")
        print("=" * 60)
        
        for scenario_id, scenario in self.scenarios.items():
            print(f"\n📋 {scenario['name']}")
            print(f"   {scenario['description']}")
            print(f"   Threat Level: {scenario['threat_level'].upper()}")
            
            for engine_name in self.engines:
                result = self.run_scenario(scenario_id, scenario, engine_name)
                self.results.append(result)
        
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive security report"""
        # Calculate summary statistics
        engine_stats = {}
        for engine_name in self.engines:
            engine_results = [r for r in self.results if r['engine'] == engine_name]
            vulnerable = sum(1 for r in engine_results if r.get('status') == 'vulnerable')
            secure = sum(1 for r in engine_results if r.get('status') == 'secure')
            
            engine_stats[engine_name] = {
                'total': len(engine_results),
                'secure': secure,
                'vulnerable': vulnerable,
                'security_score': (secure / len(engine_results) * 100) if engine_results else 0
            }
        
        # Generate markdown report
        report = f"""# Container Security Assessment Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

Tested **{len(self.scenarios)} attack scenarios** across **{len(self.engines)} execution engines**.

### Security Scores by Engine:
"""
        
        for engine, stats in engine_stats.items():
            emoji = "🛡️" if stats['security_score'] > 80 else "⚠️" if stats['security_score'] > 50 else "❌"
            report += f"- **{engine.upper()}**: {emoji} {stats['security_score']:.1f}% secure "
            report += f"({stats['secure']}/{stats['total']} scenarios blocked)\n"
        
        report += "\n## Critical Findings\n\n"
        
        # Find critical vulnerabilities
        critical_vulns = [r for r in self.results 
                         if r.get('status') == 'vulnerable' 
                         and r.get('threat_level') == 'critical']
        
        if critical_vulns:
            report += "### ❌ Critical Vulnerabilities Found:\n"
            for vuln in critical_vulns:
                report += f"- **{vuln['engine']}**: {vuln['scenario_name']}\n"
        else:
            report += "### ✅ No Critical Vulnerabilities Found\n"
        
        # Detailed results by scenario
        report += "\n## Detailed Results by Attack Scenario\n"
        
        for scenario_id, scenario in self.scenarios.items():
            report += f"\n### {scenario['name']}\n"
            report += f"**Threat Level**: {scenario['threat_level'].upper()}\n"
            report += f"**Description**: {scenario['description']}\n\n"
            
            # Results table
            report += "| Engine | Result | Details |\n"
            report += "|--------|--------|----------|\n"
            
            scenario_results = [r for r in self.results if r['scenario_id'] == scenario_id]
            for result in scenario_results:
                status_emoji = {
                    'secure': '✅',
                    'vulnerable': '❌',
                    'unknown': '⚠️',
                    'error': '💥',
                    'skipped': '⏭️'
                }.get(result.get('status', 'unknown'), '?')
                
                details = ""
                if result.get('status') == 'secure':
                    details = f"{result.get('blocked_count', 0)} attacks blocked"
                elif result.get('status') == 'vulnerable':
                    details = f"{result.get('failed_count', 0)} attacks succeeded"
                elif result.get('status') == 'error':
                    details = f"Error: {result.get('error', 'Unknown')}"
                
                report += f"| {result['engine']} | {status_emoji} {result.get('status', 'unknown').upper()} | {details} |\n"
        
        # Recommendations
        report += "\n## Security Recommendations\n\n"
        
        if engine_stats.get('subprocess', {}).get('vulnerable', 0) > 0:
            report += "1. **NEVER use subprocess in production** - It provides no isolation\n"
        
        if engine_stats.get('docker', {}).get('vulnerable', 0) > 0:
            report += "2. **Docker needs additional hardening** - Use security options like:\n"
            report += "   - `--security-opt no-new-privileges`\n"
            report += "   - `--cap-drop ALL`\n"
            report += "   - `--read-only` filesystem\n"
        
        if 'gvisor' in engine_stats:
            report += "3. **Use gVisor for untrusted code** - Provides kernel-level isolation\n"
        else:
            report += "3. **Consider gVisor** - Not currently available but recommended for production\n"
        
        report += """
## Container Security Best Practices

1. **Defense in Depth**: Use multiple layers of security
2. **Least Privilege**: Drop all capabilities not explicitly needed
3. **Network Isolation**: Use `--network none` when possible
4. **Resource Limits**: Always set memory and CPU limits
5. **Read-Only Root**: Use `--read-only` with explicit tmpfs mounts
6. **No New Privileges**: Always use `--security-opt no-new-privileges`
7. **User Namespaces**: Run as non-root user (use `--user`)

## About This Test

This security assessment simulates attacks that an AI model might attempt during evaluation:
- Container escape attempts
- Privilege escalation
- Network exfiltration
- Resource exhaustion
- Kernel exploitation
- Side-channel attacks

The goal is to ensure that even a highly capable AI system cannot break out of its evaluation sandbox.
"""
        
        # Save report
        with open('CONTAINER_SECURITY_REPORT.md', 'w') as f:
            f.write(report)
        print(f"\n\n📄 Report saved to CONTAINER_SECURITY_REPORT.md")
        
        # Also save raw results as JSON
        with open('security_test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'engines': list(self.engines.keys()),
                'scenarios': len(ATTACK_SCENARIOS),
                'results': self.results,
                'statistics': engine_stats
            }, f, indent=2)
        print(f"📊 Raw results saved to security_test_results.json")


def main():
    """Run security tests standalone"""
    print("⚠️  This script requires explicit scenario selection")
    print("Usage:")
    print("  For safe demos: import SAFE_DEMO_SCENARIOS")
    print("  For real attacks: import ATTACK_SCENARIOS (dangerous!)")
    print("")
    print("Example:")
    print("  from security_scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS")
    print("  runner = SecurityTestRunner(SAFE_DEMO_SCENARIOS, include_subprocess=True)")
    print("  runner.run_all_scenarios()")


if __name__ == '__main__':
    main()