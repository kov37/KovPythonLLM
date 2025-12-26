"""
Advanced Agent Loop for KOV with 6-layer architecture
"""

import logging
from typing import Dict, List, Any, Optional, Literal
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
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.llm = ChatOllama(model="llama3.2:3b", temperature=0.1)
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
        
        # Extract parameters using LLM
        if tool_name == "read_file_tool":
            # Simple parameter extraction for read_file
            import re
            path_match = re.search(r'(?:read|show|display)\s+(.+?)(?:\s|$)', user_input, re.IGNORECASE)
            if path_match:
                parameters = {"path": path_match.group(1).strip()}
            else:
                parameters = {"path": user_input.split()[-1] if user_input.split() else "."}
        elif tool_name == "write_file_tool":
            # Simple parameter extraction for write_file
            import re
            # Look for patterns like "create file.txt with content"
            match = re.search(r'(?:create|write)\s+(.+?)\s+(?:with|containing)\s+(.+)', user_input, re.IGNORECASE)
            if match:
                parameters = {"path": match.group(1).strip(), "content": match.group(2).strip()}
            else:
                words = user_input.split()
                if len(words) >= 2:
                    parameters = {"path": words[-1], "content": "default content"}
                else:
                    parameters = {"path": "default.txt", "content": "default content"}
        elif tool_name == "list_directory_tool":
            parameters = {"path": "."}  # Default to current directory
        elif tool_name == "run_shell_tool":
            # Extract command
            import re
            cmd_match = re.search(r'(?:run|execute)\s+(.+)', user_input, re.IGNORECASE)
            if cmd_match:
                parameters = {"command": cmd_match.group(1).strip()}
            else:
                parameters = {"command": "echo 'no command specified'"}
        else:
            # Use LLM for complex parameter extraction
            param_prompt = f"""
Extract parameters for {tool_name} from: "{user_input}"

Respond with parameters in format: param1=value1|param2=value2
If no parameters needed, respond: NONE
"""
            param_response = self.llm.invoke([SystemMessage(content=param_prompt)])
            parameters = {}
            if param_response.content.strip() != "NONE":
                for param in param_response.content.strip().split('|'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        parameters[key.strip()] = value.strip()
        
        # Execute tool
        try:
            tool_func = self.tools[tool_name]
            if parameters:
                if len(parameters) == 1:
                    output = tool_func(list(parameters.values())[0])
                else:
                    output = tool_func(**parameters)
            else:
                output = tool_func()
            
            return ToolExecution(tool_name, parameters, output, True)
        
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
                last_output = successful_executions[-1].output
                return f"Task completed successfully!\n\n{last_output}"
            else:
                return "I encountered some issues completing your request. Please try rephrasing or being more specific."
        
        except Exception as e:
            if self.debug:
                logging.error(f"Agent error: {str(e)}")
            return f"Error: {str(e)}"
