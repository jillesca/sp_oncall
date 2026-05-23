# 🚀 SP Oncall: Multi-Agent Network Investigation

[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/jillesca/sp_oncall)

SP Oncall is an experiment about a network investigation system that automates complex network diagnostics and troubleshooting for Service Provider (SP) networks. It uses artificial intelligence to analyze network devices, identify issues, and provide detailed reports. I'm mostly using it to learn and demo about AI solutions for networking.

## 🤖 What Does It Do?

Think of SP Oncall as a team of specialized AI agents that work together to investigate network problems:

- 🔍 **Input Validator** - Understands your questions and identifies which network devices to investigate.
- 📋 **Planner** - Creates a customized investigation strategy for each device.
- ⚡ **Executor** - Runs the actual network commands and collects data from your devices.
- 🎯 **Assessor** - Checks if the investigation found what you were looking for.
- 📊 **Reporter** - Creates easy-to-understand reports and remembers what it learned.

## 🎥 Quick Demo

📹 Watch [SP Oncall in Action](https://app.vidcast.io/share/71c7937d-645d-4226-87c6-883b49c0e4f3) (2:25) showing how to query the network using natural language.

![graph](img/graph.png)

## 🏗️ Architecture

The system uses a multi-agent architecture where specialized AI agents collaborate to investigate network issues. Here's how the workflow operates from user query to final report:

```mermaid
sequenceDiagram
    participant User
    participant SPOncall as SP Oncall
    participant MCP as gNMIBuddy MCP Server
    participant Devices as Network Devices

    User->>SPOncall: User query
    activate SPOncall

    Note over SPOncall: 1. Input Validator<br/>Validates query and scope
    SPOncall->>MCP: Get available devices
    activate MCP
    MCP-->>SPOncall: Device list
    deactivate MCP

    Note over SPOncall: 2. Planner<br/>Creates investigation strategy

    Note over SPOncall: 3. Executor<br/>Runs network operations
    SPOncall->>MCP: Network operations (BGP, interfaces, etc.)
    activate MCP
    MCP->>Devices: gNMI requests
    activate Devices
    Devices-->>MCP: gNMI responses
    deactivate Devices
    MCP-->>SPOncall: Structured data
    deactivate MCP

    Note over SPOncall: 4. Assessor<br/>Evaluates results

    loop Until objective achieved
        Note over SPOncall: If more data needed
        SPOncall->>MCP: Additional operations
        activate MCP
        MCP->>Devices: gNMI requests
        activate Devices
        Devices-->>MCP: gNMI responses
        deactivate Devices
        MCP-->>SPOncall: Additional data
        deactivate MCP
    end

    Note over SPOncall: 5. Reporter<br/>Generates final report
    SPOncall->>User: Investigation Report
    deactivate SPOncall
```

## 🎯 Key Features

- **Learning**: Remembers past investigations and uses that knowledge to plan better future investigations.
- **Multi-Device Processing**: Can investigate multiple network devices at the same time.
- **Flexible Targeting**: Can target devices by name, role (like "edge routers" or "core switches"), or pattern matching.
- **Self-Checking**: Automatically retries if it doesn't get the information it needs.
- **Detailed Reporting**: Creates comprehensive reports while saving insights for future use.

## 🛠️ Prerequisites

Before you can use SP Oncall, you'll need these tools installed on your system:

- **Make** - A build automation tool that helps run common commands (install via your package manager).
- **[uv](https://docs.astral.sh/uv/#installation)** - A fast Python package manager (alternative to pip).
- **[OpenAI API Key](https://platform.openai.com/)** - Required if using OpenAI models (default).
- **[LangSmith Account](https://smith.langchain.com/)** - For Langgraph Studio.
- **Network Devices** - Your actual network equipment, or use [DevNet sandbox](https://devnetsandbox.cisco.com/DevNet/) for testing

**Windows users**: This project requires a Unix-like environment. Install [WSL (Windows Subsystem for Linux)](https://docs.microsoft.com/en-us/windows/wsl/install) to run it on Windows.

## ⚡️ Quick Start Guide

### 1. Clone and install

```bash
git clone https://github.com/jillesca/sp_oncall
cd sp_oncall
make install
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Required keys:

| Variable            | Description                               |
| ------------------- | ----------------------------------------- |
| `OPENAI_API_KEY`    | OpenAI API key                            |
| `LANGSMITH_API_KEY` | LangSmith API key (for tracing)           |
| `LANGSMITH_PROJECT` | LangSmith project name (e.g. `sp_oncall`) |
| `LANGSMITH_TRACING` | Set to `true` to enable tracing           |

See the [Configuration Reference](#-configuration-reference) below for all available options.

### 3. Configure network device access

SP Oncall uses [gNMIBuddy](https://github.com/jillesca/gNMIBuddy) MCP server to query network devices. Point `mcp_config.json` at your running gNMIBuddy instance:

```json
{
  "gNMIBuddy": {
    "transport": "http",
    "url": "http://localhost:8000/mcp"
  }
}
```

### 4. Start

```bash
make run
```

This starts the LangGraph development server. Open LangGraph Studio at the URL shown in the terminal.

### 5. Send a query

In LangGraph Studio, start a new thread and type a query:

```text
Check BGP neighbors on xrd-1
How are my PE routers performing?
Investigate all core P devices
```

For the alert-driven demo flow, see [Demo Workflow](#-demo-workflow) below.

## 🧪 Testing with DevNet Sandbox

Don't have network devices? No problem! Use the [DevNet XRd Sandbox](https://devnetsandbox.cisco.com/DevNet/) - a free environment for testing.

### 🏗️ Sandbox Setup

1. Reserve the DevNet **XRd Sandbox** (free account required)
2. Follow the sandbox instructions to start the containerized SR MPLS network using Docker
3. Configure gNMI on the simulated devices (gNMI is like a modern replacement for SSH/CLI access)

To automatically configure gNMI on the XRd DevNet sandbox, you can use this helper script:

```bash
ANSIBLE_HOST_KEY_CHECKING=False \
bash -c 'TMPDIR=$(mktemp -d) \
&& trap "rm -rf $TMPDIR" EXIT \
&& curl -s https://raw.githubusercontent.com/jillesca/gNMIBuddy/refs/heads/main/ansible-helper/xrd_apply_config.yaml > "$TMPDIR/playbook.yaml" \
&& curl -s https://raw.githubusercontent.com/jillesca/gNMIBuddy/refs/heads/main/ansible-helper/hosts > "$TMPDIR/hosts" \
&& uvx --from "ansible-core==2.19.2" --with "paramiko,ansible" ansible-playbook "$TMPDIR/playbook.yaml" -i "$TMPDIR/hosts"'
```

<details>
<summary><strong>If you have problems with Ansible</strong></summary>

You can manually enable gNMI on each XRd device. Apply this configuration to all XRd devices:

```bash
grpc
 port 57777
 no-tls
```

Don't forget to `commit` your changes to XRd.

</details>

## 🔧 Configuration Reference

All `SP_ONCALL_*` variables can be set in your `.env` file. See `.env.example` for the full list with comments.

| Variable                    | Default | Description                                                                                                       |
| --------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------- |
| `SP_ONCALL_MAX_RETRIES`     | `3`     | Max execution retries per device investigation. Also overridable from LangGraph Studio.                           |
| `SP_ONCALL_LOG_LEVEL`       | `info`  | Log level for sp_oncall modules (`debug` \| `info` \| `warning` \| `error`).                                      |
| `SP_ONCALL_LANGCHAIN_DEBUG` | `false` | Enable verbose LangChain debug tracing.                                                                           |
| `SP_ONCALL_MODULE_LEVELS`   | —       | Per-module log overrides (e.g. `sp_oncall.nodes=debug,langgraph=error`). Run `make logger-names` to list modules. |
| `SP_ONCALL_LOG_FILE`        | —       | Write logs to a file in addition to stdout.                                                                       |

### AI model selection

In LangGraph Studio, click **Manage Assistants** to select the model. Available models are defined in `src/configuration.py` under `LLMModel`.

### Investigation skills

Investigation strategies live in `skills/` as Markdown files. When an alert fires, the planner selects skills based on the alert's `event_type`. For manual queries, all skills are available. See `src/util/skill_routing.py` for the routing table.

For detailed logging configuration, see [src/logging/README.md](src/logging/README.md).

---

## 🚨 Demo Workflow

The primary demo path is alert-driven: an observability system fires a webhook that triggers a background investigation, and the presenter joins the running thread in LangGraph Studio.

### Thread-per-Alert flow

1. **Alert fires** — Prometheus detects a network event and sends it to Alertmanager → Grafana → webhook container.
2. **Webhook container** (`POST /alert`) transforms the Grafana payload into a `NetworkAlert` and calls `POST /runs` on the LangGraph API.
3. **sp_oncall graph runs** in the background: `input_validator → planner → network_executor → report_generator`.
4. **Open LangGraph Studio** and join the thread by its ID to watch the investigation live.
5. **Ask follow-up questions** in the same thread — agents have full access to the investigation state.

### Triggering a test alert manually

Use `scripts/test_alert.sh` to send a fake alert to the webhook container:

```bash
# Show the curl commands without sending (dry run)
bash scripts/test_alert.sh --dry-run

# Send a specific alert type
bash scripts/test_alert.sh interface_down
bash scripts/test_alert.sh bgp_down
bash scripts/test_alert.sh isis_down
bash scripts/test_alert.sh topology_degraded
bash scripts/test_alert.sh interface_flapping
bash scripts/test_alert.sh interface_errors
```

The webhook container must be running (`docker compose up webhook-receiver`) and the LangGraph server must be reachable at `http://localhost:2024`.

## 🆘 Getting Help

- **Issues**: Check the [GitHub issues](https://github.com/jillesca/sp_oncall/issues) page
- **Questions**: Open a new issue with your question
- **Contributing**: Right now this is proof of concept experiment. Feel free to fork.

## 📚 Learn More

- **gNMI**: [gRPC Network Management Interface](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
- **LangGraph**: [LangChain's workflow framework](https://langchain-ai.github.io/langgraph/)
- **DevNet Sandbox**: [Cisco's free network simulation environment](https://devnetsandbox.cisco.com/DevNet/)
