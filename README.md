# 🚀 SP Oncall: Automated Network Diagnostics with LangGraph

SP Oncall is an intelligent agent-based system for automating network device diagnostics and health checks. It leverages [LangGraph](https://github.com/langchain-ai/langgraph) to orchestrate a graph of specialized agents, each responsible for planning, executing, assessing, and reporting on network troubleshooting tasks. The system uses [gNMIBuddy](https://github.com/jillesca/gNMIBuddy) via the MCP protocol to extract real-time data from network devices.

## 🛠️ Requirements

- [uv](https://docs.astral.sh/uv/#installation)
- Access to OpenAI or compatible LLM API
- [gNMIBuddy](https://github.com/jillesca/gNMIBuddy) (for MCP tool integration)

## ⚡️ Quick Start

1. **Set up environment variables** (required for LLM and tracing):

   Create a `.env` file in the project root with the following content:

   ```bash
   # .env file
   OPENAI_API_KEY=your-openai-key
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
   LANGSMITH_API_KEY=your-langsmith-key
   LANGSMITH_PROJECT=your-project-name
   ```

   The system will automatically load these variables at runtime. Using a `.env` file is required for correct operation with LangGraph.

2. **Run the agent system**

```bash
make run
```

This will install all dependencies and start the LangGraph workflow.

## 🔌 MCP Tool Configuration

SP Oncall uses gNMIBuddy as its main tool for extracting data from network devices. Make sure to configure the MCP client in your environment. Example configuration (see `README.md` for details):

```json
{
  "gNMIBuddy": {
    "command": "uv",
    "args": [
      "run",
      "--with",
      "mcp[cli],pygnmi,networkx",
      "mcp",
      "run",
      "/absolute/path/to/gNMIBuddy/mcp_server.py"
    ],
    "transport": "stdio",
    "env": {
      "NETWORK_INVENTORY": "/absolute/path/to/gNMIBuddy/xrd_inventory.json"
    }
  }
}
```
