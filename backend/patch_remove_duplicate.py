#!/usr/bin/env python3
"""Removes the duplicate workflow check from main.py"""

with open('main.py', 'r') as f:
    content = f.read()

old = """    existing = workflow_exists_by_name(result["workflow_name"])
    if existing:
        return {
            **result,
            "duplicate_warning": True,
            "existing_workflow_id": existing["workflow_id"]
        }

    workflow = {"""

new = """    workflow = {"""

content = content.replace(old, new)

with open('main.py', 'w') as f:
    f.write(content)

print('duplicate check removed:', 'duplicate_warning' not in content)
print('Done. Restart uvicorn.')
