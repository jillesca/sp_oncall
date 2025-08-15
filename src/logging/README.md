# sp_oncall Logging System

A comprehensive, modular logging system built for the sp_oncall project, inspired by the gNMIBuddy logging architecture and optimized for LangGraph applications.

## 🎯 Features

- **Type-safe configuration** using data classes and enums
- **Modular architecture** with single-responsibility components
- **External library suppression** specifically tuned for LangGraph, Uvicorn, and other noisy libraries
- **Environment variable configuration** for flexible deployment
- **Operation tracking** with automatic timing and context
- **Structured logging** with OpenTelemetry compatibility
- **Sequential log files** with automatic numbering

## 🚀 Quick Start

### Basic Usage

```python
from src.logging import configure_logging, get_logger

# Configure logging
configure_logging(level="info")

# Get a logger for your module
logger = get_logger(__name__)
logger.info("Hello from the logging system!")
```

### Advanced Configuration

```python
from src.logging import LoggingConfigurator

# Advanced configuration with external library suppression
LoggingConfigurator.configure(
    global_level="info",
    module_levels={
        "sp_oncall.nodes": "debug",
        "langgraph": "error",
        "uvicorn": "warning"
    },
    enable_structured=True,
    external_suppression_mode="langgraph"
)
```

## 🎨 Logger Naming Convention

All loggers follow a hierarchical naming structure:

```
sp_oncall                          # Root application
├── sp_oncall.graph                # Graph orchestration
├── sp_oncall.nodes                # Node components
│   ├── sp_oncall.nodes.planner
│   ├── sp_oncall.nodes.executor
│   ├── sp_oncall.nodes.assessor
│   └── sp_oncall.nodes.reporter
├── sp_oncall.utils                # Utilities
│   ├── sp_oncall.utils.llm
│   ├── sp_oncall.utils.plans
│   └── sp_oncall.utils.file_loader
└── sp_oncall.prompts              # Prompt templates
```

## 🔧 Operation Tracking

Automatic operation logging with timing and context:

```python
from src.logging import log_operation, get_logger

logger = get_logger(__name__)

@log_operation("plan_execution")
def execute_plan(device_name: str, plan_steps: list):
    logger.info(f"Executing plan for {device_name}")
    # Implementation...
    return result

# Output:
# 2025-08-15 10:30:00 | DEBUG | sp_oncall.nodes.planner | Starting plan_execution | operation=plan_execution function_args=('xrd-1', [...])
# 2025-08-15 10:30:01 | DEBUG | sp_oncall.nodes.planner | Completed plan_execution | operation=plan_execution duration_ms=850.23
```

## 🌐 External Library Suppression

Three strategies for different contexts:

### LangGraph Strategy (Default - Aggressive)

```python
# Suppresses noisy LangGraph, Uvicorn, watchfiles, etc.
LoggingConfigurator.configure(external_suppression_mode="langgraph")
```

### CLI Strategy (Moderate)

```python
# Moderate suppression for CLI tools
LoggingConfigurator.configure(external_suppression_mode="cli")
```

### Development Strategy (Minimal)

```python
# Minimal suppression for debugging
LoggingConfigurator.configure(external_suppression_mode="development")
```

## 📈 Environment Configuration

Control all settings via environment variables:

```bash
# Global settings
export SP_ONCALL_LOG_LEVEL=debug
export SP_ONCALL_STRUCTURED_LOGGING=true

# Module-specific levels
export SP_ONCALL_MODULE_LEVELS="sp_oncall.nodes=debug,langgraph=error"

# Suppression mode
export SP_ONCALL_EXTERNAL_SUPPRESSION_MODE=langgraph

# Debug mode
export SP_ONCALL_DEBUG_MODE=true

# Custom log file
export SP_ONCALL_LOG_FILE=/var/log/sp_oncall.log
```

## 🔍 Structured Logging

OpenTelemetry-compatible JSON output:

```python
LoggingConfigurator.configure(enable_structured=True)

# Results in JSON output:
{
  "timestamp": "2025-08-15T10:30:00.123456",
  "level": "INFO",
  "logger": "sp_oncall.nodes.executor",
  "message": "Executing network command",
  "module": "executor",
  "filename": "executor.py",
  "line_number": 45,
  "extra": {
    "device_name": "xrd-1",
    "operation": "get_interface_status",
    "duration_ms": 150.5
  }
}
```

## 📁 File Management

Sequential log files with smart numbering:

```
logs/
├── sp_oncall_001.log  # First execution
├── sp_oncall_002.log  # Second execution
└── sp_oncall_003.log  # Latest execution
```

## 🏗️ Integration with Existing Code

### Update your existing modules:

```python
# In src/nodes/planner.py
from src.logging import get_logger, log_operation

logger = get_logger(__name__)  # Creates sp_oncall.nodes.planner logger

@log_operation("plan_generation")
def planner_node(state: GraphState) -> GraphState:
    logger.info(f"Planning for objective: {state.objective}")
    # Your existing code...
    logger.debug(f"Generated {len(plan_steps)} plan steps")
    return updated_state
```

```python
# In src/graph.py
from src.logging import get_logger

logger = get_logger(__name__)  # Creates sp_oncall.graph logger

def decide_next_step(state: GraphState) -> str:
    logger.debug(f"Routing decision: objective_achieved={state.objective_achieved_assessment}")
    if state.objective_achieved_assessment:
        logger.info("Objective achieved, proceeding to report generation")
        return "report_generator"
    else:
        logger.info("Objective not achieved, continuing execution loop")
        return "network_executor"
```

### Initialize logging in your main application:

```python
# In your main application startup
from src.logging import LoggingConfigurator

# Configure logging before any other imports
LoggingConfigurator.configure(
    global_level="info",
    module_levels={
        "sp_oncall.nodes": "debug",  # Detailed node logging
        "sp_oncall.graph": "info",   # Graph orchestration info
        "langgraph": "warning",      # Reduce LangGraph noise
        "uvicorn": "error",          # Minimal web server noise
    },
    enable_external_suppression=True,
    external_suppression_mode="langgraph"
)
```

## 🧪 Testing the System

Run the demo script to see all features in action:

```bash
python3 demo_logging.py
```

## 🎯 Key Benefits

### For Development

- **Clear debugging**: Module-specific log levels help isolate issues
- **Operation tracking**: Automatic timing and context for all operations
- **Noise reduction**: External library suppression keeps logs clean

### For Operations

- **Environment control**: Full configuration via environment variables
- **Structured output**: JSON logging for log aggregation systems
- **File management**: Automatic log rotation and numbering

### For Maintenance

- **Type safety**: Enums and data classes prevent configuration errors
- **Modular design**: Easy to understand and modify individual components
- **Self-documenting**: Clear interfaces and comprehensive examples

## 📚 Available Environment Variables

| Variable                              | Description            | Default     | Example                                 |
| ------------------------------------- | ---------------------- | ----------- | --------------------------------------- |
| `SP_ONCALL_LOG_LEVEL`                 | Global log level       | `info`      | `debug`, `info`, `warning`, `error`     |
| `SP_ONCALL_MODULE_LEVELS`             | Module-specific levels | -           | `sp_oncall.nodes=debug,langgraph=error` |
| `SP_ONCALL_STRUCTURED_LOGGING`        | Enable JSON logging    | `false`     | `true`, `false`                         |
| `SP_ONCALL_LOG_FILE`                  | Custom log file path   | Sequential  | `/var/log/sp_oncall.log`                |
| `SP_ONCALL_EXTERNAL_SUPPRESSION_MODE` | Library suppression    | `langgraph` | `cli`, `langgraph`, `development`       |
| `SP_ONCALL_DEBUG_MODE`                | Enable debug mode      | `false`     | `true`, `false`                         |

## 🔗 Architecture

```
src/logging/
├── core/                    # Core types and data structures
│   ├── enums.py            # LogLevel, SuppressionMode enums
│   ├── models.py           # Configuration data classes
│   ├── logger_names.py     # Centralized logger naming
│   └── formatter.py        # Human-readable and JSON formatters
├── configuration/          # Configuration components
│   ├── environment.py      # Environment variable reading
│   ├── configurator.py     # Main logging configuration
│   └── file_utils.py       # Log file path management
├── suppression/            # External library noise reduction
│   ├── external.py         # Core suppression functionality
│   └── strategies.py       # Context-specific strategies
├── decorators/             # Operation tracking
│   └── operation.py        # @log_operation decorator
└── utils/                  # Utilities and helpers
    ├── dynamic.py          # Runtime logger management
    └── convenience.py      # Simple API functions
```

Built following the Zen of Python: "Beautiful is better than ugly. Explicit is better than implicit. Simple is better than complex."
