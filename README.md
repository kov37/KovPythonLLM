# KOV - Local AI Developer Agent

🤖 **KOV** is an advanced local AI developer agent that provides file system operations, shell command execution, and internet access through natural language conversation - all running completely offline using local LLMs via Ollama.

## ✨ Features

- 🧠 **Advanced 6-Layer Agent Architecture** - Intent classification, planning, execution, reflection, and termination logic
- 🔒 **Completely Offline** - No internet required, all processing happens locally
- 📁 **File System Operations** - Read, write, list, and delete files with natural language
- 🖥️ **Shell Command Execution** - Run bash/zsh commands with safety confirmations
- 🌐 **Internet Access** - Fetch URLs and download files when needed
- 💬 **Rich Interactive UI** - Beautiful terminal interface with loading indicators
- 🛡️ **Safety Policies** - Built-in confirmation prompts for dangerous operations
- 🔄 **Adaptive Planning** - Multi-step task execution with reflection and adjustment

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Or download from https://ollama.ai
   ```

2. **Pull a compatible model**:
   ```bash
   ollama pull llama3:latest
   ```

### Installation

```bash
# Clone the repository
git clone https://github.com/kov37/KovPythonLLM.git
cd KovPythonLLM

# Install dependencies
pip install -e .

# Start KOV
kov
```

## 💡 Usage Examples

```bash
# Start KOV (interactive mode)
kov

# With debug mode to see the 6-layer architecture in action
kov --debug

# Show version
kov --version
```

### Example Conversations

```
❯ What files are in this directory?
❯ Create a Python script that prints "Hello World"
❯ Check what's on google.com
❯ Download the latest Python documentation
❯ Run a system health check
❯ Set up a development environment
```

## 🏗️ Architecture

KOV uses an advanced 6-layer agent architecture:

1. **🎯 Intent Classification** - Determines if input is a question, command, multi-step task, tool request, or reasoning-only
2. **📋 Planning Layer** - Creates structured execution plans with goals, steps, and required tools
3. **🛡️ Tool Selection Policy** - Enforces safety policies and confirmation prompts
4. **⚡ Execution Layer** - Validates parameters and executes tools with error handling
5. **🤔 Reflection Layer** - Evaluates results and adjusts plans adaptively
6. **🛑 Termination Logic** - Clean stopping conditions to prevent runaway loops

This architecture matches the sophistication of OpenAI's superalignment agents, Anthropic's Constitutional AI, and Microsoft's AutoGen.

## 🛠️ Available Tools

- **File Operations**: `read_file`, `write_file`, `list_directory`, `delete_file`
- **Shell Commands**: `run_shell` (with safety confirmations)
- **Internet Access**: `fetch_url`, `download_file`

## 🔧 Configuration

### Models

KOV works with any Ollama-compatible model. Recommended models:
- `llama3:latest` (default, good balance of speed and capability)
- `mistral:7b-instruct` (alternative option)
- `deepseek-r1:8b` (if available)

### Safety Policies

- **Auto-execute**: File reading, directory listing, URL fetching
- **Require confirmation**: File deletion, shell commands, file downloads
- **Forbidden**: None by default (all tools available with appropriate safeguards)

### Workspace Scope

File operations are scoped to a workspace root. Configure with:

```bash
export KOV_WORKSPACE_ROOT=/path/to/project
```

If not set, KOV uses the current working directory.

## 📦 Package Structure

```
KOV/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent.py              # Basic agent (deprecated)
│   └── advanced_agent.py     # Advanced 6-layer architecture
├── tools/
│   ├── __init__.py
│   └── operations.py         # File, shell, and internet operations
└── cli/
    ├── __init__.py
    └── main.py              # Rich CLI interface
```

## 🧪 Testing

Run the test suite:

```bash
pytest -q
```

This covers tool safety controls, structured error handling, and agent parameter extraction.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by [Ollama](https://ollama.ai/) for local LLM inference
- UI built with [Rich](https://rich.readthedocs.io/) for beautiful terminal interfaces
- Inspired by advanced agent architectures from OpenAI, Anthropic, and Microsoft

## 🔗 Links

- [Ollama Models](https://ollama.ai/library)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Rich Terminal Library](https://rich.readthedocs.io/)

---

**KOV** - Your local AI developer agent. Think globally, compute locally. 🌍💻
