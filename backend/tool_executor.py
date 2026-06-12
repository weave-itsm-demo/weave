"""
tool_executor.py
Executes tools by type: MCP (GitHub), Open API (Stack Overflow), Generated (scripts).
All execution is async and streams log events via a callback.
"""

import httpx
import os
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from tool_registry import load_generated_script, save_generated_script, increment_usage

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "weave-itsm-demo")
GITHUB_REPO  = os.getenv("GITHUB_REPO",  "weave-itsm-demo")


# ── STEP 1: GitHub MCP ──────────────────────────────────────────────────────

async def execute_github_fetch(step: dict, log, issue_number: int = None) -> dict:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient() as client:

        if issue_number:
            # Fetch a specific issue by number
            await log("info", f"Connecting to GitHub MCP — {GITHUB_OWNER}/{GITHUB_REPO}")
            await log("info", f"Fetching issue #{issue_number}...")
            url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            issue = resp.json()

            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            hours_open = round((datetime.now(timezone.utc) - created).total_seconds() / 3600, 1)

            body = issue.get("body", "")
            error_sig = issue["title"]
            for line in body.split("\n"):
                if any(k in line.lower() for k in ["error", "exception", "503", "401", "400"]):
                    error_sig = line.strip()
                    break

            assignment_group = "Unassigned"
            for line in body.split("\n"):
                if "assignment group" in line.lower():
                    parts = line.split(":")
                    if len(parts) > 1:
                        assignment_group = parts[1].strip()
                    break

            incident = {
                "number": issue["number"],
                "title": issue["title"],
                "body": body[:500],
                "labels": [l["name"] for l in issue.get("labels", [])],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "hours_open": hours_open,
                "error_signature": error_sig,
                "assignment_group": assignment_group,
                "url": issue["html_url"]
            }

            await log("ok", f"Fetched issue #{issue_number}: {issue['title'][:60]}")
            await log("info", f"Labels: {', '.join(incident['labels']) or 'none'} | Open: {hours_open}h")
            increment_usage("github_mcp_fetch_incidents")
            return {"incidents": [incident], "total_count": 1, "fetched_at": datetime.now().isoformat()}

        else:
            # Fallback: fetch all open P1/P2
            await log("info", f"Connecting to GitHub MCP — {GITHUB_OWNER}/{GITHUB_REPO}")
            all_incidents = []
            for label in ["P1", "P2"]:
                url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
                params = {"state": "open", "labels": label}
                await log("info", f"Fetching issues with label={label}...")
                resp = await client.get(url, headers=headers, params=params, timeout=10)
                resp.raise_for_status()
                issues = resp.json()

                for issue in issues:
                    created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                    hours_open = round((datetime.now(timezone.utc) - created).total_seconds() / 3600, 1)
                    body = issue.get("body", "")
                    error_sig = issue["title"]
                    for line in body.split("\n"):
                        if any(k in line.lower() for k in ["error", "exception", "503", "401", "400"]):
                            error_sig = line.strip()
                            break
                    assignment_group = "Unassigned"
                    for line in body.split("\n"):
                        if "assignment group" in line.lower():
                            parts = line.split(":")
                            if len(parts) > 1:
                                assignment_group = parts[1].strip()
                            break
                    all_incidents.append({
                        "number": issue["number"],
                        "title": issue["title"],
                        "body": body[:500],
                        "labels": [l["name"] for l in issue.get("labels", [])],
                        "state": issue["state"],
                        "created_at": issue["created_at"],
                        "hours_open": hours_open,
                        "error_signature": error_sig,
                        "assignment_group": assignment_group,
                        "url": issue["html_url"]
                    })
                await log("ok", f"Fetched {len(issues)} {label} incident(s)")

            await log("ok", f"Total incidents fetched: {len(all_incidents)}")
            increment_usage("github_mcp_fetch_incidents")
            return {"incidents": all_incidents, "total_count": len(all_incidents), "fetched_at": datetime.now().isoformat()}


# ── STEP 2: Stack Overflow Open API ─────────────────────────────────────────

async def execute_stackoverflow_search(step: dict, incidents: list, log) -> dict:
    await log("info", "Connecting to Stack Exchange public API...")
    so_results = {}

    async with httpx.AsyncClient() as client:
        for inc in incidents:
            error_sig = inc.get("error_signature", inc["title"])
            query = error_sig[:100].replace("\n", " ").strip()
            await log("info", f"Searching SO for: #{inc['number']} — {query[:60]}...")

            params = {
                "order": "desc", "sort": "relevance",
                "q": query, "site": "stackoverflow",
                "pagesize": 3, "filter": "withbody"
            }

            try:
                resp = await client.get(
                    "https://api.stackexchange.com/2.3/search/advanced",
                    params=params, timeout=8
                )
                data = resp.json()
                items = data.get("items", [])
                top = items[0] if items else None

                so_results[str(inc["number"])] = {
                    "total_found": len(items),
                    "top_answer": top.get("title", "") if top else "",
                    "top_url":    top.get("link", "")  if top else "",
                    "top_score":  top.get("score", 0)  if top else 0,
                    "is_answered": top.get("is_answered", False) if top else False,
                    "answers": [
                        {"title": i.get("title",""), "url": i.get("link",""),
                         "score": i.get("score",0), "is_answered": i.get("is_answered",False)}
                        for i in items
                    ]
                }

                if items:
                    await log("ok", f"#{inc['number']} — {len(items)} result(s), top score: {top.get('score',0)}")
                else:
                    await log("warn", f"#{inc['number']} — no Stack Overflow results found")

            except Exception as e:
                await log("warn", f"#{inc['number']} — SO search failed: {str(e)[:60]}")
                so_results[str(inc["number"])] = {
                    "total_found": 0, "top_answer": "", "top_url": "",
                    "top_score": 0, "is_answered": False, "answers": []
                }

            await asyncio.sleep(0.2)

    await log("ok", f"Stack Overflow enrichment complete for {len(incidents)} incident(s)")
    increment_usage("stackoverflow_search_fixes")
    return so_results


# ── STEP 3: Resolution Plan Generator (on the fly) ───────────────────────────

RESOLUTION_PLAN_SCRIPT_TEMPLATE = '''"""
weave.generate_resolution_plan
Auto-generated by Jacquard Loom at: {timestamp}
Workflow: Incident Triage and Resolution

This script was generated on the fly by Jacquard Loom and persisted
to the tool registry for reuse on future incidents.
"""

def generate_resolution_plan(incident, so_results, workflow_id):
    """
    Takes a single incident and Stack Overflow results.
    Returns a structured resolution plan ready for human review and approval.
    """
    inc_id   = str(incident.get("number", "unknown"))
    title    = incident.get("title", "Unknown incident")
    labels   = incident.get("labels", [])
    hours    = incident.get("hours_open", 0)
    owner    = incident.get("assignment_group", "Unassigned")
    so       = so_results.get(inc_id, {{}})
    fix_url  = so.get("top_url", "")
    fix_found = so.get("total_found", 0) > 0

    priority = "P1" if "P1" in labels else "P2" if "P2" in labels else "Unknown"
    urgency  = "Immediate" if priority == "P1" else "Urgent"

    action_items = []
    if fix_url:
        action_items.append(f"Apply recommended fix: {{fix_url}}")
    else:
        action_items.append("Escalate to senior engineer — no known fix found")
    action_items.append(f"Assign to {{owner}} for immediate action")
    action_items.append("Update incident status to In Progress")
    if priority == "P1":
        action_items.append("Notify on-call lead — P1 incident")

    plan = f"""## Resolution Plan — #{{inc_id}}: {{title}}

**Priority:** {{priority}} | **Urgency:** {{urgency}} | **Open:** {{hours}}h
**Assigned To:** {{owner}}

### Recommended Fix
{{"Known fix found: " + fix_url if fix_url else "No Stack Overflow fix found — escalate immediately."}}

### Action Items
{{chr(10).join(f"{{i+1}}. {{a}}" for i, a in enumerate(action_items))}}

---
*Generated by Jacquard Loom. Requires human approval before posting to GitHub.*
"""
    return {{"resolution_plan": plan, "action_items": action_items, "priority": priority}}
'''


async def execute_resolution_plan_generator(step: dict, incidents: list, so_results: dict, workflow_id: str, log) -> dict:
    from llm_simulator import compose_briefing

    tool_id = "weave_resolution_plan_generator"
    script_exists = load_generated_script(tool_id) is not None

    if script_exists:
        await log("info", "Loading resolution plan generator from tool registry...")
        await asyncio.sleep(0.3)
        await log("ok", "Script loaded from registry")
    else:
        await log("info", "No resolution plan generator found in tool registry")
        await log("info", "Jacquard Loom is generating a new tool on the fly...")
        await asyncio.sleep(1.2)
        script_code = RESOLUTION_PLAN_SCRIPT_TEMPLATE.format(timestamp=datetime.now().isoformat())
        save_generated_script(tool_id, script_code)
        await log("ok", "Tool generated and saved to registry: weave.generate_resolution_plan")

    await log("info", "Running resolution plan generator...")
    await asyncio.sleep(0.5)

    result = await compose_briefing(incidents, so_results, workflow_id)

    inc = incidents[0] if incidents else {}
    await log("ok", f"Resolution plan generated for #{inc.get('number','?')}: {inc.get('title','')[:50]}")
    if result.get("escalations"):
        await log("warn", "Escalation required — no known fix found for this incident")

    increment_usage(tool_id)
    return result


# ── WORKFLOW ORCHESTRATOR ────────────────────────────────────────────────────

async def execute_workflow(workflow: dict, log, sandbox: bool = False, issue_number: int = None):
    steps = workflow.get("steps", [])
    results = {}

    await log("info", f"{'[SANDBOX] ' if sandbox else ''}Starting: {workflow.get('workflow_name', workflow['workflow_id'])}")
    if issue_number:
        await log("info", f"Target incident: #{issue_number}")
    await log("info", f"{len(steps)} steps to execute")
    await asyncio.sleep(0.3)

    for i, step in enumerate(steps):
        step_id = step.get("id", f"step_{i+1}")
        tool    = step.get("tool", "")

        await log("step_start", json.dumps({"step_index": i, "step_id": step_id, "title": step["title"]}))
        start = asyncio.get_event_loop().time()

        try:
            if "github" in tool:
                result = await execute_github_fetch(step, log, issue_number=issue_number)
                results["incidents"]  = result["incidents"]
                results["fetched_at"] = result["fetched_at"]

            elif "stackoverflow" in tool:
                incidents = results.get("incidents", [])
                result = await execute_stackoverflow_search(step, incidents, log)
                results["so_results"] = result

            elif "resolution_plan" in tool or "briefing" in tool or "compose" in tool:
                incidents  = results.get("incidents", [])
                so_results = results.get("so_results", {})
                result = await execute_resolution_plan_generator(step, incidents, so_results, workflow["workflow_id"], log)
                results["briefing"]     = result["briefing"]
                results["action_items"] = result["action_items"]
                results["escalations"]  = result["escalations"]
                results["summary"]      = result["summary"]

            elif "triage" in tool:
                # Legacy triage script step — kept for backward compatibility
                incidents  = results.get("incidents", [])
                so_results = results.get("so_results", {})
                from llm_simulator import generate_triage_script
                result = await generate_triage_script(incidents, so_results)
                results["scored_incidents"] = result["scored_incidents"]

            else:
                await log("warn", f"No executor found for tool: {tool} — skipping")
                result = {"status": "skipped"}

            duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
            await log("step_done", json.dumps({"step_index": i, "duration_ms": duration_ms}))

        except Exception as e:
            await log("step_error", json.dumps({"step_index": i, "error": str(e)}))
            await log("err", f"Step failed: {str(e)[:120]}")

    await log("info", "Workflow execution complete")
    return results
