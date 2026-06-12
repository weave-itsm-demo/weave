#!/usr/bin/env python3
"""
Patches main.py to add POST /api/workflow/{workflow_id}/post-comment endpoint.
Run from ~/weave/backend/:  python3 post_comment_patch.py
"""
import os, re

MAIN_PY = 'main.py'

# New Pydantic model for the request
NEW_MODEL = """
class PostCommentRequest(BaseModel):
    issue_number: int
    comment: str
"""

# New endpoint
NEW_ENDPOINT = """
@app.post("/api/workflow/{workflow_id}/post-comment")
async def post_github_comment(workflow_id: str, req: PostCommentRequest):
    import httpx
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo  = os.getenv("GITHUB_REPO")

    if not token or not owner or not repo:
        raise HTTPException(status_code=500, detail="GitHub credentials not configured")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{req.issue_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json={"body": req.comment})

    if resp.status_code == 201:
        data = resp.json()
        return {
            "posted": True,
            "comment_url": data["html_url"],
            "issue_number": req.issue_number
        }
    else:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"GitHub API error: {resp.text}"
        )
"""

with open(MAIN_PY, 'r') as f:
    content = f.read()

# Inject model before the @app.get("/api/health") line
if 'PostCommentRequest' not in content:
    content = content.replace(
        '@app.get("/api/health")',
        NEW_MODEL + '\n@app.get("/api/health")'
    )
    print('Model injected.')
else:
    print('Model already present.')

# Inject endpoint before the WebSocket handler
if 'post-comment' not in content:
    content = content.replace(
        '@app.websocket("/ws/execute/{workflow_id}")',
        NEW_ENDPOINT + '\n@app.websocket("/ws/execute/{workflow_id}")'
    )
    print('Endpoint injected.')
else:
    print('Endpoint already present.')

with open(MAIN_PY, 'w') as f:
    f.write(content)

print('Done. Restart uvicorn to pick up changes.')
