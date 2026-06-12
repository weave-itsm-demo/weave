"""
tool_registry.py
Manages the Weave tool registry — load, save, add, delete, and match tools.
Tools persist in tools/tools.json. Generated scripts persist in tools/generated/.
"""

import json
import os
import aiofiles
from datetime import datetime
from typing import Optional

TOOLS_PATH = os.path.join(os.path.dirname(__file__), "tools", "tools.json")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "tools", "generated")


def load_tools() -> list:
    try:
        with open(TOOLS_PATH, "r") as f:
            data = json.load(f)
            return data.get("tools", [])
    except FileNotFoundError:
        return []


def save_tools(tools: list):
    with open(TOOLS_PATH, "w") as f:
        json.dump({"tools": tools}, f, indent=2)


def get_all_tools() -> list:
    return load_tools()


def get_tool_by_id(tool_id: str) -> Optional[dict]:
    tools = load_tools()
    return next((t for t in tools if t["id"] == tool_id), None)


def add_tool(tool: dict) -> dict:
    tools = load_tools()
    existing = next((t for t in tools if t["id"] == tool["id"] or t["name"] == tool["name"]), None)
    if existing:
        raise ValueError(f"Tool '{tool['name']}' already exists")
    tools.append(tool)
    save_tools(tools)
    return tool


def delete_tool(tool_id: str) -> bool:
    tools = load_tools()
    original_count = len(tools)
    tools = [t for t in tools if t["id"] != tool_id]
    if len(tools) == original_count:
        return False
    save_tools(tools)
    script_path = os.path.join(GENERATED_DIR, f"{tool_id}.py")
    if os.path.exists(script_path):
        os.remove(script_path)
    return True


def toggle_tool(tool_id: str, enabled: bool) -> Optional[dict]:
    tools = load_tools()
    for t in tools:
        if t["id"] == tool_id:
            t["enabled"] = enabled
            save_tools(tools)
            return t
    return None


def increment_usage(tool_id: str):
    tools = load_tools()
    for t in tools:
        if t["id"] == tool_id:
            t["usage"] = t.get("usage", 0) + 1
            save_tools(tools)
            return


def save_generated_script(tool_id: str, script_code: str):
    os.makedirs(GENERATED_DIR, exist_ok=True)
    script_path = os.path.join(GENERATED_DIR, f"{tool_id}.py")
    with open(script_path, "w") as f:
        f.write(script_code)


def load_generated_script(tool_id: str) -> Optional[str]:
    script_path = os.path.join(GENERATED_DIR, f"{tool_id}.py")
    if os.path.exists(script_path):
        with open(script_path, "r") as f:
            return f.read()
    return None


def generated_script_exists(tool_id: str) -> bool:
    return os.path.exists(os.path.join(GENERATED_DIR, f"{tool_id}.py"))


def match_step_to_tool(step: dict, tools: list) -> Optional[dict]:
    step_tool = step.get("tool", "").lower()
    step_title = step.get("title", "").lower()
    step_type = step.get("type", "").lower()

    for t in tools:
        if t.get("enabled", True) and t["name"].lower() == step_tool:
            return t

    for t in tools:
        if t.get("enabled", True) and step_tool and step_tool in t["name"].lower():
            return t

    for t in tools:
        if t.get("enabled", True) and t.get("category") == step_type:
            return t

    return None
