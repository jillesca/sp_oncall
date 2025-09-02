# Debug Object Capture System

This system provides an easy mechanism to capture complex objects to log files for offline analysis and testing, solving the problem where debuggers truncate or modify object representations.

## Quick Start

### 1. Basic Debug Capture

Add this to any function where you want to capture objects:

```python
from src.logging import debug_capture_object

# Capture any object
debug_capture_object(my_complex_object, label="my_object")
```

### 2. Conditional Debug Capture

For production-safe debugging that only activates when needed:

```python
from src.logging import conditional_debug_capture

# Only captures if SP_ONCALL_DEBUG_CAPTURE=1 is set
conditional_debug_capture(
    problematic_object,
    label="debug_issue_123"
)
```

### 3. Capture with Context

When you need additional context around the object:

```python
from src.logging import debug_capture_with_context

context = {
    "function_name": "process_data",
    "user_query": user_query,
    "step": "validation",
    "timestamp": datetime.now().isoformat()
}

debug_capture_with_context(
    complex_object,
    context=context,
    label="validation_issue"
)
```

## Environment Variables

Control debug capture behavior with environment variables:

- `SP_ONCALL_DEBUG_CAPTURE=1` - Enable general debug capture
- `SP_ONCALL_DEBUG_MCP=1` - Enable MCP-specific debug capture

Set them in your shell:

```bash
export SP_ONCALL_DEBUG_CAPTURE=1
export SP_ONCALL_DEBUG_MCP=1
```

## File Locations

Debug files are saved to:

- `logs/debug/` - Main debug capture directory
- Files are named with timestamps: `debug_object_20250818_143022_123.txt`
- Session logs: `debug_capture_20250818_143022.log`

## Output Formats

Objects are captured in multiple formats:

1. **JSON** - Structured, easy to copy-paste into code
2. **Pretty Print** - Human-readable format
3. **Repr** - Python representation
4. **String** - String representation (optional)

## Example Capture File

```
# Debug Capture: mcp_response_raw_20250818_143022_123
# Timestamp: 2025-08-18T14:30:22.123456
# Object Type: dict
# Object Class: <class 'dict'>

============================================================
# FORMAT: JSON
============================================================

{
  "content": "router1, router2, switch1",
  "metadata": {
    "timestamp": "2025-08-18T14:30:22",
    "source": "mcp_agent"
  },
  "status": "success"
}

============================================================
# FORMAT: PPRINT
============================================================

{'content': 'router1, router2, switch1',
 'metadata': {'source': 'mcp_agent', 'timestamp': '2025-08-18T14:30:22'},
 'status': 'success'}

============================================================
# FORMAT: REPR
============================================================

{'content': 'router1, router2, switch1', 'metadata': {'timestamp': '2025-08-18T14:30:22', 'source': 'mcp_agent'}, 'status': 'success'}
```

## Using Captured Objects for Testing

### 1. Copy Object from Capture File

1. Run your application with debug capture enabled
2. Find the capture file in `logs/debug/`
3. Copy the JSON or repr representation
4. Paste into your test script

## Integration Examples

### In Input Validator (Current Example)

```python
def _extract_mcp_response_content(mcp_response: dict) -> str:
    # Always capture for debugging
    debug_capture_object(
        mcp_response,
        label="mcp_response_raw",
        formats=['json', 'pprint', 'repr']
    )

    # Conditional capture (only when debugging MCP issues)
    conditional_debug_capture(
        mcp_response,
        label="mcp_response_conditional",
        env_var="SP_ONCALL_DEBUG_MCP"
    )

    # Your existing logic...
```

### In Error Handling

```python
except Exception as e:
    # Capture the problematic object when errors occur
    debug_capture_with_context(
        problematic_object,
        context={
            "error": str(e),
            "function": "_extract_mcp_response_content",
            "traceback": traceback.format_exc()
        },
        label="error_analysis"
    )
    raise
```

## Best Practices

1. **Use descriptive labels** - `"mcp_response_validation_error"` instead of `"debug"`
2. **Include context** - Use `debug_capture_with_context` for complex scenarios
3. **Use conditional capture** - Avoid performance impact in production
4. **Clean up regularly** - Debug files can accumulate over time
5. **Document capture points** - Add comments explaining why you're capturing

## Performance Considerations

- Debug capture adds minimal overhead when disabled
- JSON serialization may be slow for very large objects
- Use conditional capture for production environments
- Consider capturing only relevant parts of large objects

## Troubleshooting

### Object Not JSON Serializable

The system automatically handles non-serializable objects by:

1. Trying JSON first
2. Falling back to `__dict__` representation
3. Always providing repr and pprint formats

### Missing Capture Files

Check:

1. Environment variables are set correctly
2. `logs/debug/` directory exists and is writable
3. No exceptions during capture (check main logs)

### Large Objects

For very large objects:

1. Use `formats=['repr']` to capture only essential format
2. Consider capturing only relevant parts
3. Use context capture to include summaries instead of full objects

## Advanced Usage

### Custom Debug Capture Instance

```python
from src.logging import DebugCapture

# Create custom instance with different directory
debug = DebugCapture(debug_dir="custom/debug/path")
debug.capture_object(obj, "custom_label")
```

### Programmatic Analysis

```python
from pathlib import Path
import json

# Find all debug files
debug_dir = Path("logs/debug")
for file in debug_dir.glob("*_mcp_response_*.txt"):
    print(f"Found capture: {file}")
    # Process capture files programmatically
```
