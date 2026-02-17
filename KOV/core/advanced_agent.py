"""
Advanced Agent Loop for KOV with 6-layer architecture
"""

import logging
import shlex
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from KOV.tools.operations import read_file, write_file, list_dir, delete_file, run_shell, fetch_url, download_file


class IntentType(Enum):
    QUESTION = "question"
    COMMAND = "command"
    MULTI_STEP_TASK = "multi_step_task"
    TOOL_REQUEST = "tool_request"
    REASONING_ONLY = "reasoning_only"


class ToolPolicy(Enum):
    REQUIRE_CONFIRMATION = "require_confirmation"
    AUTO_EXECUTE = "auto_execute"
    FORBIDDEN = "forbidden"


@dataclass
class Intent:
    type: IntentType
    confidence: float
    description: str


@dataclass
class Plan:
    goal: str
    steps: List[str]
    tools_needed: List[str]
    estimated_complexity: int


@dataclass
class ToolExecution:
    tool_name: str
    parameters: Dict[str, Any]
    output: Any
    success: bool
    error: Optional[str] = None


@dataclass
class Reflection:
    output_matches_expectation: bool
    plan_still_valid: bool
    next_step_adjustment: Optional[str]
    additional_context_needed: bool


class AdvancedKOVAgent:
    """Advanced KOV Agent with 6-layer architecture"""
    
    def __init__(self, debug: bool = False, model: str = "llama3:latest"):
        self.debug = debug
        self.model = model
        self.llm = ChatOllama(model=model, temperature=0.1)
        self.conversation_history = []
        
        # Tool policies
        self.tool_policies = {
            "run_shell_tool": ToolPolicy.REQUIRE_CONFIRMATION,
            "delete_file_tool": ToolPolicy.REQUIRE_CONFIRMATION,
            "write_file_tool": ToolPolicy.AUTO_EXECUTE,
            "read_file_tool": ToolPolicy.AUTO_EXECUTE,
            "list_directory_tool": ToolPolicy.AUTO_EXECUTE,
            "fetch_url_tool": ToolPolicy.AUTO_EXECUTE,
            "download_file_tool": ToolPolicy.REQUIRE_CONFIRMATION,
        }
        
        # Available tools
        self.tools = {
            "read_file_tool": read_file,
            "write_file_tool": lambda path, content: write_file({"path": path, "content": content}),
            "list_directory_tool": list_dir,
            "delete_file_tool": delete_file,
            "run_shell_tool": run_shell,
            "fetch_url_tool": fetch_url,
            "download_file_tool": download_file,
        }

    def _extract_tool_parameters(self, tool_name: str, user_input: str) -> Dict[str, Any]:
        """Extract tool parameters using deterministic parsing with safe defaults."""
        tokens = shlex.split(user_input) if user_input.strip() else []
        lowered = user_input.lower()

        if tool_name == "list_directory_tool":
            if " in " in lowered:
                return {"path": user_input.split(" in ", 1)[1].strip().strip("'\"") or "."}
            return {"path": "."}

        if tool_name in {"read_file_tool", "delete_file_tool"}:
            if " " in user_input:
                candidate = user_input.split(" ", 1)[1].strip().strip("'\"")
                return {"path": candidate or "."}
            return {"path": "."}

        if tool_name == "run_shell_tool":
            command_text = user_input
            for prefix in ("run ", "execute ", "shell "):
                if lowered.startswith(prefix):
                    command_text = user_input[len(prefix):]
                    break
            return {"command": command_text.strip()}

        if tool_name == "write_file_tool":
            # Expected pattern: write <path> with <content>
            if " with " in lowered:
                lhs, rhs = user_input.split(" with ", 1)
                lhs_tokens = shlex.split(lhs)
                path = lhs_tokens[-1] if lhs_tokens else "output.txt"
                return {"path": path, "content": rhs}
            if len(tokens) >= 2:
                return {"path": tokens[-1], "content": "default content"}
            return {"path": "output.txt", "content": "default content"}

        if tool_name == "fetch_url_tool":
            for token in tokens:
                if token.startswith("http://") or token.startswith("https://"):
                    return {"url": token}
            return {"url": user_input.strip()}

        if tool_name == "download_file_tool":
            url = ""
            filename = "downloaded.file"
            for token in tokens:
                if token.startswith("http://") or token.startswith("https://"):
                    url = token
            if " to " in lowered:
                filename = user_input.split(" to ", 1)[1].strip().strip("'\"") or filename
            return {"url": url, "filename": filename}

        return {}

    def _format_tool_output(self, execution: ToolExecution) -> str:
        """Render structured tool output for user response."""
        output = execution.output
        if isinstance(output, dict):
            if output.get("ok"):
                data = output.get("data")
                if isinstance(data, list):
                    return "\n".join(str(item) for item in data)
                return str(data)
            return output.get("error", "Tool execution failed")
        return str(output)
    
    def classify_intent(self, user_input: str) -> Intent:
        """Layer 1: Intent Classification"""
        prompt = f"""
Classify this user input into ONE category:

Input: "{user_input}"

Categories:
- QUESTION: Asking for information (What, How, Why questions)
- COMMAND: Direct instruction to do something (Create, Delete, Run)
- MULTI_STEP_TASK: Complex task needing multiple steps (setup, configure, build)
- TOOL_REQUEST: Specific tool usage (use curl, execute command, run script)
- REASONING_ONLY: Pure thinking task (explain, calculate, tell joke)

Respond ONLY with: CATEGORY|0.9|description
Example: COMMAND|0.9|User wants to create a file
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        parts = response.content.strip().split('|')
        
        try:
            if len(parts) >= 3:
                intent_type = IntentType(parts[0].lower().strip())
                confidence = float(parts[1])
                description = parts[2]
            else:
                # Better fallback logic
                user_lower = user_input.lower()
                if any(word in user_lower for word in ['what', 'how', 'why', 'where', 'when']):
                    if any(word in user_lower for word in ['explain', 'tell me', 'calculate']):
                        intent_type = IntentType.REASONING_ONLY
                    else:
                        intent_type = IntentType.QUESTION
                elif any(word in user_lower for word in ['create', 'delete', 'make', 'build']):
                    intent_type = IntentType.COMMAND
                elif any(word in user_lower for word in ['run', 'execute', 'use', 'curl']):
                    intent_type = IntentType.TOOL_REQUEST
                elif any(word in user_lower for word in ['setup', 'configure', 'install']):
                    intent_type = IntentType.MULTI_STEP_TASK
                else:
                    intent_type = IntentType.REASONING_ONLY
                confidence = 0.7
                description = "Fallback classification"
        except ValueError:
            # If enum value is invalid, use fallback
            intent_type = IntentType.QUESTION
            confidence = 0.5
            description = "Invalid classification, defaulted to question"
        
        return Intent(intent_type, confidence, description)
    
    def create_plan(self, user_input: str, intent: Intent) -> Plan:
        """Layer 2: Planning"""
        if intent.type == IntentType.REASONING_ONLY:
            return Plan("Provide reasoning", ["Think and respond"], [], 1)
        
        prompt = f"""
Create a plan for: "{user_input}"
Intent: {intent.type.value}

Respond with:
GOAL: [clear goal statement]
STEPS: [step1] | [step2] | [step3]
TOOLS: [tool1] | [tool2]
COMPLEXITY: [1-5]

Available tools: read_file_tool, write_file_tool, list_directory_tool, delete_file_tool, run_shell_tool, fetch_url_tool, download_file_tool
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        lines = response.content.strip().split('\n')
        
        goal = "Complete user request"
        steps = ["Execute request"]
        tools_needed = []
        complexity = 1
        
        for line in lines:
            if line.startswith('GOAL:'):
                goal = line[5:].strip()
            elif line.startswith('STEPS:'):
                steps = [s.strip() for s in line[6:].split('|')]
            elif line.startswith('TOOLS:'):
                tools_needed = [t.strip() for t in line[6:].split('|') if t.strip()]
            elif line.startswith('COMPLEXITY:'):
                try:
                    complexity = int(line[11:].strip())
                except:
                    complexity = 1
        
        return Plan(goal, steps, tools_needed, complexity)
    
    def select_and_execute_tool(self, tool_name: str, user_input: str, plan: Plan) -> ToolExecution:
        """Layer 3 & 4: Tool Selection Policy + Execution"""
        if tool_name not in self.tools:
            return ToolExecution(tool_name, {}, None, False, "Tool not found")
        
        # Check policy
        policy = self.tool_policies.get(tool_name, ToolPolicy.AUTO_EXECUTE)
        
        if policy == ToolPolicy.FORBIDDEN:
            return ToolExecution(tool_name, {}, None, False, "Tool forbidden by policy")
        
        if policy == ToolPolicy.REQUIRE_CONFIRMATION:
            confirm = input(f"Execute {tool_name}? (y/N): ")
            if confirm.lower() != 'y':
                return ToolExecution(tool_name, {}, None, False, "User cancelled")
        
        # Extract parameters using deterministic parsing
        parameters = self._extract_tool_parameters(tool_name, user_input)
        
        # Execute tool
        try:
            tool_func = self.tools[tool_name]
            output = tool_func(**parameters) if parameters else tool_func()
            success = bool(isinstance(output, dict) and output.get("ok"))

            if tool_name == "run_shell_tool" and isinstance(output, dict):
                success = success and bool(output.get("meta", {}).get("succeeded", False))

            error_message = None
            if not success:
                if isinstance(output, dict):
                    error_message = output.get("error", "Tool failed")
                else:
                    error_message = "Tool failed"
            return ToolExecution(tool_name, parameters, output, success, error_message)
        
        except Exception as e:
            return ToolExecution(tool_name, parameters, None, False, str(e))
    
    def reflect(self, execution: ToolExecution, plan: Plan, step_index: int) -> Reflection:
        """Layer 5: Reflection"""
        if not execution.success:
            return Reflection(False, True, f"Retry {execution.tool_name} with different parameters", True)
        
        # Simple reflection logic
        output_valid = execution.output is not None and str(execution.output).strip() != ""
        plan_valid = step_index < len(plan.steps)
        
        return Reflection(output_valid, plan_valid, None, False)
    
    def should_terminate(self, plan: Plan, executions: List[ToolExecution], step_index: int) -> bool:
        """Layer 6: Termination Logic"""
        # Goal achieved - all steps completed
        if step_index >= len(plan.steps):
            return True
        
        # Error state - too many failures
        failed_executions = [e for e in executions if not e.success]
        if len(failed_executions) >= 3:
            return True
        
        # Safety boundary - too many tool calls
        if len(executions) >= 10:
            return True
        
        return False
    
    def run(self, user_input: str) -> str:
        """Main execution loop with 6-layer architecture"""
        try:
            # Layer 1: Intent Classification
            intent = self.classify_intent(user_input)
            if self.debug:
                print(f"Intent: {intent.type.value} (confidence: {intent.confidence})")
            
            # Layer 2: Planning
            plan = self.create_plan(user_input, intent)
            if self.debug:
                print(f"Plan: {plan.goal} | Steps: {len(plan.steps)} | Tools: {plan.tools_needed}")
            
            # Handle reasoning-only requests
            if intent.type == IntentType.REASONING_ONLY:
                response = self.llm.invoke([
                    SystemMessage(content="You are KOV, a helpful AI assistant. Provide a thoughtful response."),
                    HumanMessage(content=user_input)
                ])
                return response.content
            
            # Execution loop
            executions = []
            step_index = 0
            
            while not self.should_terminate(plan, executions, step_index):
                if step_index >= len(plan.steps):
                    break
                
                current_step = plan.steps[step_index]
                
                # Determine which tool to use for this step
                if plan.tools_needed and step_index < len(plan.tools_needed):
                    tool_name = plan.tools_needed[step_index]
                elif plan.tools_needed:
                    tool_name = plan.tools_needed[0]  # Use first tool if not enough specified
                else:
                    # No tools needed, just reasoning
                    response = self.llm.invoke([
                        SystemMessage(content=f"Complete this step: {current_step}"),
                        HumanMessage(content=user_input)
                    ])
                    return response.content
                
                # Layer 3 & 4: Tool Selection + Execution
                execution = self.select_and_execute_tool(tool_name, user_input, plan)
                executions.append(execution)
                
                # Layer 5: Reflection
                reflection = self.reflect(execution, plan, step_index)
                
                if not reflection.output_matches_expectation and execution.success:
                    # Tool succeeded but output unexpected - continue anyway
                    pass
                
                if not reflection.plan_still_valid:
                    break
                
                step_index += 1
            
            # Generate final response
            successful_executions = [e for e in executions if e.success]
            if successful_executions:
                last_execution = successful_executions[-1]
                rendered = self._format_tool_output(last_execution)
                return f"Task completed successfully.\n\n{rendered}"

            failed = [e for e in executions if not e.success]
            if failed:
                reasons = "; ".join(e.error or "Unknown error" for e in failed[:3])
                return f"I could not complete your request. Failure details: {reasons}"

            return "I encountered issues completing your request. Please rephrase with explicit paths or commands."
        
        except Exception as e:
            if self.debug:
                logging.error(f"Agent error: {str(e)}")
            return f"Error: {str(e)}"
