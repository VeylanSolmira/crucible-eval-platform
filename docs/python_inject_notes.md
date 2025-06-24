Robust Python Code Handling Strategy

  1. Input Validation

  import ast
  import re

  def validate_python_code(code: str) -> tuple[bool, str]:
      """Validate Python code before execution"""
      # Check for syntax errors
      try:
          ast.parse(code)
      except SyntaxError as e:
          return False, f"Syntax error: {e}"

      # Check for dangerous imports/operations
      dangerous_patterns = [
          r'import\s+os',
          r'import\s+subprocess',
          r'__import__',
          r'eval\(',
          r'exec\(',
          r'compile\(',
          r'open\(',
          r'file\(',
      ]

      for pattern in dangerous_patterns:
          if re.search(pattern, code):
              return False, f"Potentially dangerous 
  operation: {pattern}"

      return True, "Code validated"

  2. Secure Container Execution

  - Use gVisor or Firecracker for enhanced isolation
  - Set strict resource limits (CPU, memory, disk)
  - Network isolation by default
  - Read-only filesystem except for specific directories
  - Drop all capabilities except required ones

  3. Code Sanitization

  def sanitize_code_for_container(code: str) -> str:
      """Prepare code for safe container execution"""
      # Escape special characters that might break shell 
  commands
      # But preserve Python syntax

      # Add timeout wrapper
      wrapped_code = f"""
  import signal
  import sys

  def timeout_handler(signum, frame):
      print("\\nExecution timed out!", file=sys.stderr)
      sys.exit(1)

  signal.signal(signal.SIGALRM, timeout_handler)
  signal.alarm(30)  # 30 second timeout

  try:
  {textwrap.indent(code, '    ')}
  finally:
      signal.alarm(0)  # Cancel alarm
  """
      return wrapped_code

  4. API Request Validation

  from pydantic import BaseModel, validator

  class CodeExecutionRequest(BaseModel):
      code: str
      timeout: int = 30
      memory_limit: str = "512M"

      @validator('code')
      def validate_code_length(cls, v):
          if len(v) > 100_000:  # 100KB limit
              raise ValueError('Code too long')
          return v

      @validator('timeout')
      def validate_timeout(cls, v):
          if v < 1 or v > 300:  # 5 minute max
              raise ValueError('Timeout must be between 1 
  and 300 seconds')
          return v
