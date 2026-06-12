#!/usr/bin/env python3
"""Patches main.py to accept optional workflow_name in /api/build"""
import os

with open('main.py', 'r') as f:
    content = f.read()

old = """async def build_workflow(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None)
):"""

new = """async def build_workflow(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    workflow_name: Optional[str] = Form(None)
):"""

old_result = """    result = await llm_simulator.extract_steps(prompt, file_content)

    existing = workflow_exists_by_name(result["workflow_name"])"""

new_result = """    result = await llm_simulator.extract_steps(prompt, file_content)
    if workflow_name:
        result["workflow_name"] = workflow_name

    existing = workflow_exists_by_name(result["workflow_name"])"""

content = content.replace(old, new)
content = content.replace(old_result, new_result)

with open('main.py', 'w') as f:
    f.write(content)

print('workflow_name param added:', 'workflow_name: Optional[str]' in content)
print('result override added:', 'result["workflow_name"] = workflow_name' in content)
