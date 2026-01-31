"""
Debug logging utilities for backend debugging.
Set DEBUG_ENABLED = True to enable logging.
"""
import json
import os
from datetime import datetime

DEBUG_ENABLED = False  # Set to True to enable debug logging
DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')


def debug_log(location, message, data=None, hypothesis_id=''):
    """
    Log debug information to file.
    
    Args:
        location: File location (e.g., 'app.py:273')
        message: Log message
        data: Dictionary of data to log
        hypothesis_id: Hypothesis identifier for debugging
    """
    if not DEBUG_ENABLED:
        return
    
    if data is None:
        data = {}
    
    log_entry = {
        'location': location,
        'message': message,
        'data': data,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'sessionId': 'debug-session',
        'runId': 'run1',
        'hypothesisId': hypothesis_id
    }
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
        
        # Append log entry as NDJSON
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        # Silently fail if logging fails
        pass

