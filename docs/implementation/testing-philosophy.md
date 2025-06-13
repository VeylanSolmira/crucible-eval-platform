# Testing Philosophy for AI Safety Evaluation

## Core Principle: Safety Through Verification

**In AI safety evaluation, untested safety measures are equivalent to no safety measures.**

This document outlines our testing philosophy and implementation strategy for the Crucible Evaluation Platform.

## Testing Architecture

### 1. TestableComponent Base Class

Every component in our system inherits from `TestableComponent`:

```python
class TestableComponent(ABC):
    @abstractmethod
    def self_test(self) -> Dict[str, Any]:
        """Quick diagnostic tests - run at every startup"""
        pass
    
    @abstractmethod
    def get_test_suite(self) -> unittest.TestSuite:
        """Comprehensive unit tests - run by default"""
        pass
```

### 2. Two-Layer Testing Strategy

#### Layer 1: self_test() - Quick Diagnostics
- **Purpose**: Rapid sanity checks
- **When**: Every component initialization
- **Duration**: Milliseconds
- **Examples**:
  - Can the engine execute code?
  - Is monitoring recording events?
  - Are safety limits configured?

#### Layer 2: get_test_suite() - Comprehensive Tests
- **Purpose**: Full safety verification
- **When**: Platform startup (by default)
- **Duration**: Seconds to minutes
- **Examples**:
  - Network isolation verification
  - Filesystem protection validation
  - Resource limit enforcement
  - Attack scenario simulations

## Test Execution Policy

### Default Behavior: FULL Testing

```python
# Normal startup - runs ALL tests
python extreme_mvp.py

# Output:
Running FULL test suite (default for safety)...
test_network_isolation ... ok
test_filesystem_readonly ... ok
test_resource_limits ... ok
...
Platform starting only after all tests pass.
```

### Development Override (Use with Extreme Caution)

```python
# Quick tests only - DANGEROUS
CRUCIBLE_TEST_LEVEL=QUICK python extreme_mvp.py

# WARNING: Running only quick tests (UNSAFE MODE)
# Full safety verification skipped!
# AI models could exploit untested vulnerabilities!

# No tests - EXTREMELY DANGEROUS
CRUCIBLE_TEST_LEVEL=NONE python extreme_mvp.py

# DANGER: All tests skipped! 
# Press Enter to continue at your own risk...
```

### Production Enforcement

**CRITICAL**: In production environments, test overrides MUST be disabled:

```python
# Production code should include:
if os.environ.get('PRODUCTION') == 'true':
    # Force full testing, ignore any override attempts
    test_level = 'FULL'
    if os.environ.get('CRUCIBLE_TEST_LEVEL') != 'FULL':
        print("ERROR: Test overrides are FORBIDDEN in production!")
        sys.exit(1)
```

## Why This Matters for AI Safety

### 1. AI Models Are Adversarial

Unlike traditional software, AI models may actively try to:
- Exploit security vulnerabilities
- Bypass safety measures
- Hide malicious capabilities
- Persist beyond evaluation sessions

### 2. Silent Failures Are Catastrophic

A failing test in AI evaluation could mean:
- **Network isolation broken** → Model exfiltrates data
- **Filesystem protection failed** → Model persists malicious code
- **Resource limits not enforced** → Model conducts denial of service
- **Monitoring compromised** → Model hides its activities

### 3. "It Worked Yesterday" Is Not Enough

AI safety requires continuous verification because:
- Container runtime updates could introduce vulnerabilities
- System configuration changes could weaken isolation
- New attack vectors are discovered regularly
- Models become more capable over time

## Test Categories

### 1. Safety-Critical Tests (Cannot Skip)

```python
def test_network_isolation(self):
    """Verify no network access is possible"""
    result = self.engine.execute(
        "import urllib.request; urllib.request.urlopen('http://example.com')"
    )
    self.assertIn('Network is unreachable', result['output'])

def test_filesystem_isolation(self):
    """Verify filesystem is read-only"""
    result = self.engine.execute(
        "open('/tmp/test.txt', 'w').write('exploit')"
    )
    self.assertIn('Read-only file system', result['output'])
```

### 2. Operational Tests (Important but Skippable in Dev)

```python
def test_monitoring_persistence(self):
    """Verify events are recorded correctly"""
    # Less critical - system works without perfect monitoring
    
def test_queue_ordering(self):
    """Verify FIFO processing"""
    # Important for fairness but not safety
```

### 3. Performance Tests (Optional in Dev)

```python
def test_evaluation_throughput(self):
    """Verify system can handle load"""
    # Run only in performance testing environments
```

## Implementation Guidelines

### 1. Every New Component Must Be Testable

```python
# BAD - No testing support
class NewFeature:
    def do_something(self):
        pass

# GOOD - Testable from day one
class NewFeature(TestableComponent):
    def do_something(self):
        pass
    
    def self_test(self):
        # Verify it works
    
    def get_test_suite(self):
        # Comprehensive tests
```

### 2. Tests Should Reveal Dangers

```python
# BAD - Test hides the problem
def test_file_access(self):
    try:
        result = execute("open('/etc/passwd')")
        self.fail("Should not be able to read files")
    except:
        pass  # Assuming exception means safe

# GOOD - Test exposes the danger
def test_file_access(self):
    result = execute("open('/etc/passwd', 'r').read()")
    if 'root:' in result['output']:
        # In subprocess mode, this SHOULD succeed - that's the danger!
        self.assertEqual(self.engine_type, 'subprocess', 
                        'File access succeeded - need Docker!')
```

### 3. Test Evolution Tracks Feature Evolution

As we add features, tests must evolve:

1. **Subprocess** → Test that filesystem access WORKS (to show danger)
2. **Docker** → Test that filesystem access FAILS (to verify safety)
3. **Monitoring** → Test event capture and retrieval
4. **Queue** → Test concurrent execution safety
5. **Kubernetes** → Test pod isolation and limits

## Testing in CI/CD

```yaml
# Example CI pipeline
stages:
  - quick_tests    # self_test() only - fast feedback
  - full_tests     # get_test_suite() - comprehensive
  - safety_tests   # Special safety-critical suite
  - deploy         # Only if ALL tests pass

# Production deployment MUST include:
deploy:
  script:
    - CRUCIBLE_TEST_LEVEL=FULL python -m pytest
    - if [ $? -ne 0 ]; then exit 1; fi
    - # Deploy only after tests pass
```

## The Ultimate Test: Red Team Exercises

Beyond automated tests, conduct regular red team exercises:

1. **Escape Attempts** - Try to break out of containment
2. **Resource Attacks** - Try to exhaust system resources  
3. **Deception Tests** - Try to hide malicious behavior
4. **Persistence Tests** - Try to survive beyond session

Document all findings and add regression tests.

## Conclusion

In AI safety evaluation, testing is not a development practice - it's a core safety mechanism. Every execution without proper testing is a potential escape route for a malicious AI model.

**Remember**: The AI models we're evaluating may be adversarial. Our tests are the locks on the cage. Would you trust a cage if you hadn't tested the locks?