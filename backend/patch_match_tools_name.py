#!/usr/bin/env python3
"""Patches main.py to save workflow_name from match-tools request"""

with open('main.py', 'r') as f:
    content = f.read()

# Add workflow_name to MatchToolsRequest
old_model = """class MatchToolsRequest(BaseModel):
    workflow_id: str
    steps: list"""

new_model = """class MatchToolsRequest(BaseModel):
    workflow_id: str
    steps: list
    workflow_name: Optional[str] = None"""

# Update match_tools handler to save the name
old_handler = """    if workflow:
        workflow["tool_matches"] = matches
        workflow["status"] = "validated"
        save_workflow(workflow)
    return {"matches": matches}"""

new_handler = """    if workflow:
        workflow["tool_matches"] = matches
        workflow["status"] = "validated"
        if req.workflow_name:
            workflow["workflow_name"] = req.workflow_name
        save_workflow(workflow)
    return {"matches": matches}"""

content = content.replace(old_model, new_model)
content = content.replace(old_handler, new_handler)

with open('main.py', 'w') as f:
    f.write(content)

print('model updated:', 'workflow_name: Optional[str]' in content)
print('handler updated:', 'req.workflow_name' in content)
print('Done. Restart uvicorn.')
