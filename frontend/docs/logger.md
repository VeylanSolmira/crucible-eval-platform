# Frontend Logger Documentation

## Overview

The logger utility provides a configurable logging system for the frontend application with different log levels and formatting options.

## Usage

### Basic Usage

```typescript
import { log } from '@/src/utils/logger'

// Different log levels
log.debug('Debug message', { extra: 'data' })
log.info('Info message')
log.warn('Warning message')
log.error('Error message', error)

// Timing operations
const endTimer = log.time('expensive-operation')
// ... do work ...
endTimer() // logs: "expensive-operation: 123ms"

// Group related logs
log.group('API Calls', () => {
  log.info('Request 1')
  log.info('Request 2')
})
```

### Configuration

#### Environment Variable

Set the default log level in your `.env.local`:

```bash
NEXT_PUBLIC_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARN, ERROR, NONE
```

#### Runtime Configuration

You can change the log level at runtime (useful for debugging):

```typescript
import logger, { LogLevel } from '@/src/utils/logger'

// Change log level
logger.setLevel(LogLevel.DEBUG)

// Configure multiple options
logger.configure({
  level: LogLevel.INFO,
  includeTimestamp: true,
  includePrefix: true,
})
```

#### Browser Console

In development mode, the logger is exposed on the window object:

```javascript
// In browser console
__logger.setLevel(0) // Enable DEBUG
__logger.configure({ includeTimestamp: true })
__logger.getConfig() // View current config
```

## Log Levels

| Level | Value | Description                        |
| ----- | ----- | ---------------------------------- |
| DEBUG | 0     | Detailed information for debugging |
| INFO  | 1     | General informational messages     |
| WARN  | 2     | Warning messages                   |
| ERROR | 3     | Error messages                     |
| NONE  | 4     | Disable all logging                |

## Features

### Automatic Configuration

- Production: Only ERROR level logs by default
- Development: INFO level logs with timestamps
- Configuration persists in localStorage

### Performance

- No-op functions when logging is disabled
- Minimal overhead in production
- Lazy evaluation of expensive log data

### Format Options

- **includeTimestamp**: Add ISO timestamp to logs
- **includePrefix**: Add [LEVEL] prefix to logs

## Best Practices

1. **Use appropriate log levels**
   - DEBUG: Detailed flow, variable values
   - INFO: Important events, state changes
   - WARN: Recoverable issues, deprecations
   - ERROR: Errors that need attention

2. **Remove debug logs before PR**
   - Keep only essential INFO/WARN/ERROR logs
   - Use DEBUG for temporary debugging

3. **Structure log data**

   ```typescript
   log.info('User action', {
     action: 'submit_evaluation',
     evalId: result.eval_id,
     duration: endTime - startTime,
   })
   ```

4. **Performance considerations**
   - Avoid logging in tight loops
   - Use log.time() for performance measurements
   - Group related logs to reduce noise
