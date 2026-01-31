# Debug Logging Infrastructure

This project includes a formalized debug logging system for easier troubleshooting during development and future updates.

## Overview

Debug logging is **disabled by default** to avoid performance overhead. It can be enabled when needed for debugging.

## Files

- **`debug_utils.py`**: Backend debug logging utility
- **`static/js/main.js`**: Contains `debugLog()` function for frontend logging

## Enabling Debug Logging

### Frontend (JavaScript)

In `static/js/main.js`, line 15:
```javascript
const DEBUG_ENABLED = false; // Change to true
```

### Backend (Python)

In `debug_utils.py`, line 6:
```python
DEBUG_ENABLED = False  # Change to True
```

## Usage

### Frontend

```javascript
debugLog('main.js:123', 'Function entry', { 
    param1: value1, 
    param2: value2 
}, 'hypothesis-A');
```

### Backend

```python
from debug_utils import debug_log

debug_log('app.py:273', 'Function entry', {
    'param1': value1,
    'param2': value2
}, 'hypothesis-A')
```

## Log Output

### Frontend
- Logs are sent via HTTP POST to the debug server endpoint
- Falls back silently if server is unavailable
- Format: NDJSON (one JSON object per line)

### Backend
- Logs are written to `.cursor/debug.log`
- Format: NDJSON (one JSON object per line)
- File is created automatically

## Log Format

```json
{
  "location": "file.js:123",
  "message": "Description of log entry",
  "data": {
    "key": "value"
  },
  "timestamp": 1234567890123,
  "sessionId": "debug-session",
  "runId": "run1",
  "hypothesisId": "A"
}
```

## Strategic Logging Points

The following locations have debug logging instrumentation:

1. **DOMContentLoaded** - Page initialization, library availability
2. **refreshData entry** - When data refresh starts
3. **Before API calls** - Request parameters
4. **API responses received** - Response status codes
5. **JSON parsed** - Data parsing success
6. **updateChart** - Plotly chart updates
7. **initializePlotlyCharts** - Chart initialization
8. **initializeLeafletMap** - Map initialization
9. **Error catch blocks** - Error details and stack traces

## Best Practices

1. **Enable only when debugging** - Keep `DEBUG_ENABLED = false` in production
2. **Use descriptive messages** - Make logs easy to understand
3. **Include relevant data** - Log parameters, return values, state
4. **Use hypothesisId** - Tag logs with hypothesis identifiers when debugging specific issues
5. **Clear logs between runs** - Delete `.cursor/debug.log` before new debugging sessions

## Example Debug Session

1. Set `DEBUG_ENABLED = true` in both files
2. Clear log file: `rm .cursor/debug.log` (or delete via file manager)
3. Reproduce the issue
4. Read logs: `cat .cursor/debug.log | jq` (or open in editor)
5. Analyze logs to identify root cause
6. Fix the issue
7. Verify fix with logs
8. Set `DEBUG_ENABLED = false` when done

## Troubleshooting

- **Logs not appearing**: Check that `DEBUG_ENABLED` is set to `true`/`True`
- **Frontend logs missing**: Check browser console for network errors to debug server
- **Backend logs missing**: Check file permissions on `.cursor/debug.log`
- **Log file too large**: Clear it periodically during long debugging sessions

