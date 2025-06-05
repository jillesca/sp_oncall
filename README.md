# SP Oncall

## Run

```bash
make run
```

## Add MCP tools

Example with gNMIBuddy

> [!NOTE]  
> If using gNMIBuddy, use absolute paths.

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
      "/Users/jillesca/DevNet/cisco_live/25clus/gNMIBuddy/mcp_server.py"
    ],
    "transport": "stdio",
    "env": {
      "NETWORK_INVENTORY": "/Users/jillesca/DevNet/cisco_live/25clus/gNMIBuddy/xrd_inventory.json"
    }
  }
}
```

## Notes

- Try with:
  - `ollama run hermes3`
  - `ollama run qwen3:14b`
  - `ollama run mistral-nemo`
  - `ollama run mixtral:8x7b`
  - Qwen2.5 coder instruct 14b
  - Mistral-small3.1
  - Gemma 3 12b
- test with smaller models like phi for getting arguments for tool calling.
- Useful advice. <https://www.reddit.com/r/n8n/comments/1j25ten/comment/mfpx786/>
- review Berkeley Function-Calling Leaderboard - <https://gorilla.cs.berkeley.edu/leaderboard.html>
