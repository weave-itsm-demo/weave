"""
main.py
Weave — Agentic Workflow Automation
FastAPI backend — all endpoints + WebSocket execution stream
"""

import json
import asyncio
import os
import random
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import llm_simulator
from tool_registry import (
    get_all_tools, get_tool_by_id, add_tool, delete_tool,
    toggle_tool, save_generated_script, load_generated_script
)
from workflow_store import (
    save_workflow, load_workflow, load_all_workflows,
    load_published_workflows, delete_workflow, delete_all_workflows,
    update_workflow_status, workflow_exists_by_name
)
from tool_executor import execute_workflow

load_dotenv()

app = FastAPI(title="Weave API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


class StepEditRequest(BaseModel):
    workflow_id: str
    step_id: str
    instruction: str
    current_step: dict

class MatchToolsRequest(BaseModel):
    workflow_id: str
    steps: list
    workflow_name: Optional[str] = None

class ToolAddRequest(BaseModel):
    name: str
    system: str
    category: str
    description: str
    inputs: list
    outputs: list
    endpoint: str
    enabled: bool = True
    integration_type: Optional[str] = None
    auth_type: Optional[str] = None
    auth_key_name: Optional[str] = None
    script: Optional[str] = None

class ToolGenerateRequest(BaseModel):
    name: str
    description: str = ""
    system: str = "weave"
    category: str = "logic"



class PostCommentRequest(BaseModel):
    issue_number: int
    comment: str

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.now().isoformat()}


@app.post("/api/build")
async def build_workflow(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    workflow_name: Optional[str] = Form(None)
):
    file_content = None
    if file:
        raw = await file.read()
        try:
            file_content = raw.decode("utf-8")
        except Exception:
            file_content = f"[binary file: {file.filename}]"

    result = await llm_simulator.extract_steps(prompt, file_content)
    if workflow_name:
        result["workflow_name"] = workflow_name

    workflow = {
        **result,
        "prompt": prompt,
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tool_matches": [],
        "execution_results": None,
        "sandbox_results": None
    }
    save_workflow(workflow)
    return result


@app.post("/api/steps/edit")
async def edit_step(req: StepEditRequest):
    updated_step = await llm_simulator.edit_step(req.current_step, req.instruction)
    workflow = load_workflow(req.workflow_id)
    if workflow:
        steps = workflow.get("steps", [])
        for i, s in enumerate(steps):
            if s["id"] == req.step_id:
                steps[i] = updated_step
                break
        workflow["steps"] = steps
        save_workflow(workflow)
    return {"step": updated_step}


@app.post("/api/steps/match-tools")
async def match_tools(req: MatchToolsRequest):
    matches = await llm_simulator.match_tools(req.steps)
    workflow = load_workflow(req.workflow_id)
    if workflow:
        workflow["tool_matches"] = matches
        workflow["status"] = "validated"
        if req.workflow_name:
            workflow["workflow_name"] = req.workflow_name
        save_workflow(workflow)
    return {"matches": matches}


@app.post("/api/workflow/{workflow_id}/sandbox")
async def sandbox_run(workflow_id: str):
    workflow = load_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "sandbox_started", "workflow_id": workflow_id}


@app.post("/api/workflow/{workflow_id}/publish")
async def publish_workflow(workflow_id: str):
    workflow = update_workflow_status(workflow_id, "published")
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "published", "workflow_id": workflow_id, "workflow": workflow}


@app.get("/api/workflows")
def get_workflows():
    return {"workflows": load_all_workflows()}


@app.get("/api/workflows/published")
def get_published():
    return {"workflows": load_published_workflows()}


@app.get("/api/workflow/{workflow_id}")
def get_workflow(workflow_id: str):
    wf = load_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@app.delete("/api/workflow/{workflow_id}")
def remove_workflow(workflow_id: str):
    deleted = delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": True, "workflow_id": workflow_id}


@app.delete("/api/workflows/all")
def reset_all_workflows():
    delete_all_workflows()
    return {"reset": True, "timestamp": datetime.now().isoformat()}


@app.get("/api/tools")
def get_tools():
    return {"tools": get_all_tools()}


@app.post("/api/tools")
def create_tool(req: ToolAddRequest):
    tool_id = req.name.replace(".", "_").replace(" ", "_").lower() + "_" + str(random.randint(1000, 9999))
    tool = {
        "id": tool_id,
        "name": req.name,
        "system": req.system,
        "type": "custom",
        "category": req.category,
        "description": req.description,
        "inputs": req.inputs,
        "outputs": req.outputs,
        "endpoint": req.endpoint,
        "enabled": req.enabled,
        "usage": 0,
        "generated": False,
        "created_at": datetime.now().isoformat(),
        **({"integration_type": req.integration_type} if req.integration_type else {}),
        **({"auth_type": req.auth_type} if req.auth_type else {}),
        **({"auth_key_name": req.auth_key_name} if req.auth_key_name else {}),
        **({"script": req.script} if req.script else {}),
    }
    try:
        saved = add_tool(tool)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/tools/generate")
async def generate_tool_schema(req: ToolGenerateRequest):
    schema = await llm_simulator.generate_tool_schema(req.name, req.description, req.system, req.category)
    return schema


@app.delete("/api/tools/{tool_id}")
def remove_tool(tool_id: str):
    deleted = delete_tool(tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"deleted": True, "tool_id": tool_id}


@app.patch("/api/tools/{tool_id}/toggle")
def toggle(tool_id: str, enabled: bool):
    tool = toggle_tool(tool_id, enabled)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool



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

@app.websocket("/ws/execute/{workflow_id}")
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

    workflow = load_workflow(workflow_id)
    if not workflow:
        await websocket.send_json({"type": "error", "message": "Workflow not found"})
        await websocket.close()
        return

    sandbox = workflow.get("status") != "published"
    step_index_tracker = {"current": -1}

    async def log(level: str, message: str):
        try:
            if level == "step_start":
                data = json.loads(message)
                step_index_tracker["current"] = data["step_index"]
                await websocket.send_json({
                    "type": "step_start",
                    "step_index": data["step_index"],
                    "step_id": data.get("step_id"),
                    "title": data.get("title")
                })
            elif level == "step_done":
                data = json.loads(message)
                await websocket.send_json({
                    "type": "step_done",
                    "step_index": data["step_index"],
                    "duration_ms": data.get("duration_ms", 0)
                })
            elif level == "step_error":
                data = json.loads(message)
                await websocket.send_json({
                    "type": "step_error",
                    "step_index": data["step_index"],
                    "error": data.get("error", "Unknown error")
                })
            else:
                await websocket.send_json({
                    "type": "step_log",
                    "step_index": step_index_tracker["current"],
                    "level": level,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception:
            pass

    try:
        results = await execute_workflow(workflow, log, sandbox=sandbox, issue_number=issue_number)

        workflow["execution_results"] = results
        workflow["last_run_at"] = datetime.now().isoformat()
        if sandbox:
            workflow["sandbox_results"] = results
            update_workflow_status(workflow_id, "sandbox_tested")
        save_workflow(workflow)

        await websocket.send_json({
            "type": "workflow_done",
            "summary": results.get("summary", {}),
            "briefing": results.get("briefing", ""),
            "action_items": results.get("action_items", []),
            "escalations": results.get("escalations", [])
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
