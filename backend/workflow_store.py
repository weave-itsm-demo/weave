"""
workflow_store.py
Persists workflows as JSON files in the workflows/ directory.
Each workflow is a single JSON file named {workflow_id}.json.
"""

import json
import os
import glob
from datetime import datetime
from typing import Optional

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")


def _ensure_dir():
    os.makedirs(WORKFLOWS_DIR, exist_ok=True)


def _path(workflow_id: str) -> str:
    return os.path.join(WORKFLOWS_DIR, f"{workflow_id}.json")


def save_workflow(workflow: dict) -> dict:
    _ensure_dir()
    workflow["updated_at"] = datetime.now().isoformat()
    with open(_path(workflow["workflow_id"]), "w") as f:
        json.dump(workflow, f, indent=2)
    return workflow


def load_workflow(workflow_id: str) -> Optional[dict]:
    path = _path(workflow_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def load_all_workflows() -> list:
    _ensure_dir()
    workflows = []
    for path in glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")):
        try:
            with open(path, "r") as f:
                workflows.append(json.load(f))
        except Exception:
            continue
    workflows.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
    return workflows


def load_published_workflows() -> list:
    return [w for w in load_all_workflows() if w.get("status") == "published"]


def delete_workflow(workflow_id: str) -> bool:
    path = _path(workflow_id)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def delete_all_workflows():
    _ensure_dir()
    for path in glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")):
        os.remove(path)


def update_workflow_status(workflow_id: str, status: str) -> Optional[dict]:
    workflow = load_workflow(workflow_id)
    if not workflow:
        return None
    workflow["status"] = status
    workflow[f"{status}_at"] = datetime.now().isoformat()
    return save_workflow(workflow)


def workflow_exists_by_name(name: str) -> Optional[dict]:
    all_wf = load_all_workflows()
    name_lower = name.lower()
    for wf in all_wf:
        if wf.get("workflow_name", "").lower() == name_lower:
            return wf
    return None
