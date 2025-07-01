# Remaining Linting Issues - Week 4 Day 2

## Summary: 52 Errors Across 26 Files

### Files with Most Errors:
1. **shared/generated/python/__init__.py** (6 errors)
   - 1 F403: Star import usage
   - 5 F405: Names may be undefined from star imports
   - Fix: Convert to explicit imports

2. **tests/test_components.py** (5 errors)
   - 4 E722: Bare except statements
   - 1 F841: Unused variable `api_http`
   - Nature: Test code, lower priority

3. **storage-worker/app.py** (4 errors)
   - 3 E402: Import not at top of file
   - 1 F401: Unused import
   - Fix: Reorganize imports

4. **src/security_scanner/safe_security_check.py** (4 errors)
   - Likely bare excepts and import issues
   - Security-related, should fix

5. **demos/run_demo_servers.py** (4 errors)
   - Demo code, lower priority

6. **api/legacy/openapi_validator.py** (4 errors)
   - Legacy code, consider removing entirely

### Error Types Breakdown:
- **19 E722**: Bare except statements (security/stability risk)
- **10 F841**: Unused variables (code cleanup)
- **5 F401**: Unused imports (code cleanup)
- **5 F405**: Undefined from star imports (potential bugs)
- **4 E402**: Import order issues (style)
- **3 F821**: Undefined names (potential bugs)
- **6 others**: Various minor issues

### Priority for Fixes:

#### High Priority (Core Services):
- api/microservices_gateway.py (2 errors)
- storage-service/app.py (1 error)
- storage-worker/app.py (4 errors)
- queue-service/app.py (2 errors)

#### Medium Priority (Security/Stability):
- src/security_scanner/safe_security_check.py (4 errors)
- src/execution_engine/execution.py (2 errors)
- shared/generated/python/__init__.py (6 errors)

#### Low Priority (Tests/Demos/Legacy):
- tests/* (8 errors total)
- demos/* (5 errors total)
- api/legacy/* (6 errors total)

### Recommendation:
Focus on fixing High and Medium priority files first (19 errors), which would bring us down to 33 errors mostly in test/demo code.