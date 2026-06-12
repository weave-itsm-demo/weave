#!/usr/bin/env python3
"""
Patches main.py to pass issue_number from WebSocket query params to execute_workflow.
Run from ~/weave/backend/:  python3 main_ws_patch.py
"""
import os

MAIN_PY = 'main.py'

with open(MAIN_PY, 'r') as f:
    content = f.read()

# 1. Update WebSocket handler signature to accept Request for query params
old_ws_start = '''@app.websocket("/ws/execute/{workflow_id}")
async def ws_execute(websocket: WebSocket, workflow_id: str):
    await websocket.accept()

    workflow = load_workflow(workflow_id)'''

new_ws_start = '''@app.websocket("/ws/execute/{workflow_id}")
async def ws_execute(websocket: WebSocket, workflow_id: str):
    await websocket.accept()

    # Extract issue number from query params (?issue=42)
    issue_param = websocket.query_params.get("issue", None)
    issue_number = None
    if issue_param:
        try:
            issue_number = int(str(issue_param).replace("#", "").strip())
        except (ValueError, TypeError):
            issue_number = None

    workflow = load_workflow(workflow_id)'''

# 2. Pass issue_number to execute_workflow
old_execute = '        results = await execute_workflow(workflow, log, sandbox=sandbox)'
new_execute = '        results = await execute_workflow(workflow, log, sandbox=sandbox, issue_number=issue_number)'

content = content.replace(old_ws_start, new_ws_start)
content = content.replace(old_execute, new_execute)

with open(MAIN_PY, 'w') as f:
    f.write(content)

print('issue_number extracted:', 'issue_number = None' in content)
print('passed to execute_workflow:', 'issue_number=issue_number' in content)
print('Done. Restart uvicorn to pick up changes.')
