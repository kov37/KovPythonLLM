from KOV.core.advanced_agent import AdvancedKOVAgent, Plan, ToolPolicy


def build_agent_for_test():
    agent = AdvancedKOVAgent.__new__(AdvancedKOVAgent)
    agent.debug = False
    agent.model = "test-model"
    agent.llm = None
    agent.conversation_history = []
    agent.tool_policies = {
        "run_shell_tool": ToolPolicy.AUTO_EXECUTE,
        "delete_file_tool": ToolPolicy.AUTO_EXECUTE,
        "write_file_tool": ToolPolicy.AUTO_EXECUTE,
        "read_file_tool": ToolPolicy.AUTO_EXECUTE,
        "list_directory_tool": ToolPolicy.AUTO_EXECUTE,
        "fetch_url_tool": ToolPolicy.AUTO_EXECUTE,
        "download_file_tool": ToolPolicy.AUTO_EXECUTE,
    }
    return agent


def test_extract_download_parameters():
    agent = build_agent_for_test()
    params = agent._extract_tool_parameters(
        "download_file_tool",
        "download https://example.com/file.txt to docs/file.txt",
    )
    assert params["url"] == "https://example.com/file.txt"
    assert params["filename"] == "docs/file.txt"


def test_extract_run_shell_parameters():
    agent = build_agent_for_test()
    params = agent._extract_tool_parameters("run_shell_tool", "run ls -la")
    assert params == {"command": "ls -la"}


def test_select_and_execute_tool_marks_failure_from_result():
    agent = build_agent_for_test()
    agent.tools = {
        "list_directory_tool": lambda **_: {"ok": False, "data": None, "error": "boom", "meta": {}}
    }
    plan = Plan(goal="x", steps=["y"], tools_needed=["list_directory_tool"], estimated_complexity=1)

    execution = agent.select_and_execute_tool("list_directory_tool", "list files", plan)
    assert execution.success is False
    assert execution.error == "boom"


def test_select_and_execute_tool_marks_success():
    agent = build_agent_for_test()
    agent.tools = {
        "list_directory_tool": lambda **_: {"ok": True, "data": ["a.txt"], "error": None, "meta": {}}
    }
    plan = Plan(goal="x", steps=["y"], tools_needed=["list_directory_tool"], estimated_complexity=1)

    execution = agent.select_and_execute_tool("list_directory_tool", "list files", plan)
    assert execution.success is True
    assert execution.error is None
    assert execution.output["data"] == ["a.txt"]
