"""
llm_simulator.py
Simulates LLM responses for Weave.
Swap this for llm_real.py when a real API key is available.
Same function signatures and return contracts throughout.
"""

import asyncio
import random
import json
from datetime import datetime

def detect_workflow(prompt: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ["incident", "p1", "p2", "triage", "outage", "bug", "503", "down", "alert", "resolution plan", "github", "stack overflow"]):
        return "itsm_incident_triage_resolution"
    if any(k in p for k in ["vendor", "supplier", "procurement onboard", "vendor onboard"]):
        return "vendor_onboarding"
    if any(k in p for k in ["onboard", "new hire", "employee", "provision", "hr", "training", "welcome", "joining"]):
        return "hr_employee_onboarding"
    if any(k in p for k in ["escalat", "customer", "csm", "sla", "account", "case", "support tier"]):
        return "csm_escalation_response"
    if any(k in p for k in ["purchase order", "po ", "procurement", "approval", "vendor", "invoice", "finance"]):
        return "fin_po_approval"
    if any(k in p for k in ["change request", "change management", "cab", "risk assessment", "deployment", "release"]):
        return "itsm_change_risk"
    return "itsm_incident_triage_resolution"


WORKFLOW_STEPS = {
    "itsm_incident_triage_resolution": {
        "name": "Incident Triage and Resolution",
        "steps": [
            {
                "id": "step_1", "title": "Fetch incident details from GitHub",
                "type": "query", "tool": "github.fetch_incidents",
                "description": "Use the GitHub MCP server to fetch the full details of the specific incident by issue number, including title, description, labels, assignees, and current status.",
                "input_fields": "owner, repo, issue_number",
                "output_fields": "incident, labels, assignee, status, created_at"
            },
            {
                "id": "step_2", "title": "Search Stack Overflow for known resolutions",
                "type": "query", "tool": "stackoverflow.search_fixes",
                "description": "Extract the error signature and key terms from the incident and query the Stack Exchange public API to find relevant answers and known resolutions for similar past incidents.",
                "input_fields": "error_signature, tags, limit",
                "output_fields": "answers, total_found, top_answer, top_url, top_score"
            },
            {
                "id": "step_3", "title": "Generate incident resolution plan",
                "type": "action", "tool": "weave.generate_resolution_plan",
                "description": "Synthesise the incident details, triage score, and Stack Overflow resolution data into a structured resolution plan. The plan is presented to the assignee for review and approval before being posted to the GitHub incident.",
                "input_fields": "incident, so_results, workflow_id",
                "output_fields": "resolution_plan, action_items, requires_escalation"
            }
        ]
    },
    "hr_employee_onboarding": {
        "name": "Employee Onboarding",
        "steps": [
            {
                "id": "step_1", "title": "Fetch new hire record from HR system",
                "type": "query", "tool": "workday.employee_api",
                "description": "Retrieve the new hire's profile, role, department, start date, and manager from the HR system.",
                "input_fields": "employee_id, fields",
                "output_fields": "employee_record, role, department, manager, start_date"
            },
            {
                "id": "step_2", "title": "Provision accounts and access",
                "type": "action", "tool": "okta.provision_user",
                "description": "Create Active Directory account, provision email, Slack, and assign role-based application access via Okta.",
                "input_fields": "email, first_name, last_name, role, groups",
                "output_fields": "user_id, activation_token, provisioned_apps"
            },
            {
                "id": "step_3", "title": "Assign mandatory training modules",
                "type": "action", "tool": "servicenow.table_api",
                "description": "Assign onboarding training modules based on role and department. Set completion deadlines and notify the learning management system.",
                "input_fields": "employee_id, role, department",
                "output_fields": "assigned_modules, due_dates, lms_record"
            },
            {
                "id": "step_4", "title": "Schedule introductory meetings",
                "type": "action", "tool": "google.calendar_api",
                "description": "Automatically schedule 1:1 meetings with the manager, team lead, and key stakeholders during the first week.",
                "input_fields": "employee_email, manager_email, team_emails, start_date",
                "output_fields": "meeting_ids, calendar_links, invite_status"
            },
            {
                "id": "step_5", "title": "Send welcome email with first-day instructions",
                "type": "notify", "tool": "smtp.mcp",
                "description": "Send a personalised welcome email with first-day instructions, provisioned credentials, office access details, and a link to the onboarding portal.",
                "input_fields": "employee_email, employee_name, role, start_date",
                "output_fields": "message_id, delivery_status"
            }
        ]
    },
    "csm_escalation_response": {
        "name": "Customer Escalation Response",
        "steps": [
            {
                "id": "step_1", "title": "Fetch customer account and health score",
                "type": "query", "tool": "servicenow.table_api",
                "description": "Retrieve the customer account record, current health score, contract tier, and renewal date from the CRM.",
                "input_fields": "account_id, fields",
                "output_fields": "account_record, health_score, tier, renewal_date"
            },
            {
                "id": "step_2", "title": "Pull recent case history",
                "type": "query", "tool": "servicenow.table_api",
                "description": "Fetch the last 10 support cases for this account, including resolution times and CSAT scores.",
                "input_fields": "account_id, limit, date_range",
                "output_fields": "cases, avg_resolution_time, csat_score"
            },
            {
                "id": "step_3", "title": "Evaluate routing and SLA criteria",
                "type": "logic", "tool": "servicenow.flow_logic",
                "description": "Determine the correct support tier, check SLA breach risk, and decide whether executive escalation is required.",
                "input_fields": "account_record, case_history, sla_policy",
                "output_fields": "routing_decision, sla_status, escalation_required"
            },
            {
                "id": "step_4", "title": "Notify account executive and support lead",
                "type": "notify", "tool": "slack.mcp",
                "description": "Send an escalation alert to the account executive and support lead via Slack with account context and recommended actions.",
                "input_fields": "ae_email, support_lead, account_summary, escalation_reason",
                "output_fields": "notification_sent, message_ts"
            },
            {
                "id": "step_5", "title": "Draft initial response for agent review",
                "type": "action", "tool": "weave.generate_resolution_plan",
                "description": "Generate a personalised draft response for the customer based on case history and escalation context. Requires agent review before sending.",
                "input_fields": "account_record, case_summary, tone",
                "output_fields": "draft_response, suggested_actions"
            }
        ]
    },
    "fin_po_approval": {
        "name": "Purchase Order Approval",
        "steps": [
            {
                "id": "step_1", "title": "Fetch PO record and vendor details",
                "type": "query", "tool": "sap.po_api",
                "description": "Retrieve the purchase order record including amount, vendor, line items, and requestor details from SAP.",
                "input_fields": "po_number, vendor_id",
                "output_fields": "po_record, vendor_details, line_items, total_amount"
            },
            {
                "id": "step_2", "title": "Evaluate approval routing rules",
                "type": "logic", "tool": "servicenow.flow_logic",
                "description": "Determine the correct approval chain based on PO amount, department budget, and vendor tier.",
                "input_fields": "po_record, approval_policy, department",
                "output_fields": "approval_chain, required_approvers, escalation_threshold"
            },
            {
                "id": "step_3", "title": "Notify approvers via email",
                "type": "notify", "tool": "smtp.mcp",
                "description": "Send approval request emails to each approver in the chain with PO summary and a direct approval link.",
                "input_fields": "approvers, po_summary, approval_link",
                "output_fields": "emails_sent, delivery_status"
            },
            {
                "id": "step_4", "title": "Update PO state on approval decision",
                "type": "action", "tool": "sap.po_api",
                "description": "Update the PO record in SAP with the approval decision, timestamp, and approver details. Trigger procurement workflow if approved.",
                "input_fields": "po_number, decision, approver_id, timestamp",
                "output_fields": "po_status, procurement_triggered, audit_log"
            }
        ]
    },
    "vendor_onboarding": {
        "name": "Vendor Onboarding",
        "steps": [
            {
                "id": "step_1", "title": "Validate vendor details and compliance status",
                "type": "query", "tool": "servicenow.table_api",
                "description": "Retrieve and validate the vendor's business registration, compliance certifications, and risk profile from the procurement system.",
                "input_fields": "vendor_id, validation_rules",
                "output_fields": "vendor_record, compliance_status, risk_tier"
            },
            {
                "id": "step_2", "title": "Run background and financial risk check",
                "type": "logic", "tool": "weave.generate_resolution_plan",
                "description": "Weave generates a vendor risk assessment script on the fly, scoring the vendor by financial stability, compliance history, and contract risk.",
                "input_fields": "vendor_record, risk_weights",
                "output_fields": "risk_score, risk_level, flags, script_code"
            },
            {
                "id": "step_3", "title": "Set up vendor account in procurement system",
                "type": "action", "tool": "sap.po_api",
                "description": "Create the vendor master record in SAP, assign vendor category, payment terms, and link to the appropriate cost centre.",
                "input_fields": "vendor_details, category, payment_terms, cost_centre",
                "output_fields": "vendor_id, account_number, setup_status"
            },
            {
                "id": "step_4", "title": "Provision vendor portal access",
                "type": "action", "tool": "okta.provision_user",
                "description": "Create a vendor portal account with role-based access limited to relevant procurement modules.",
                "input_fields": "vendor_email, vendor_name, access_role",
                "output_fields": "portal_user_id, activation_link, access_granted"
            },
            {
                "id": "step_5", "title": "Send onboarding pack and contract for review",
                "type": "notify", "tool": "smtp.mcp",
                "description": "Email the vendor their onboarding documentation, portal credentials, and contract for review and digital signature.",
                "input_fields": "vendor_email, vendor_name, contract_link, portal_link",
                "output_fields": "email_sent, delivery_status"
            }
        ]
    },
    "itsm_change_risk": {
        "name": "Change Request Risk Assessment",
        "steps": [
            {
                "id": "step_1", "title": "Fetch change request and affected CIs",
                "type": "query", "tool": "cmdb.query_api",
                "description": "Retrieve the change request record and all affected configuration items from the CMDB, including dependency maps.",
                "input_fields": "change_id, relationship_depth",
                "output_fields": "change_record, affected_cis, dependencies"
            },
            {
                "id": "step_2", "title": "Evaluate historical failure rate",
                "type": "logic", "tool": "weave.generate_resolution_plan",
                "description": "Weave generates a risk scoring script on the fly that analyses historical change failure rates for the affected CI group.",
                "input_fields": "affected_cis, change_history, time_window",
                "output_fields": "failure_rate, risk_indicators, script_code"
            },
            {
                "id": "step_3", "title": "Score overall change risk",
                "type": "logic", "tool": "servicenow.flow_logic",
                "description": "Calculate a composite risk score based on CI criticality, failure rate, current incident load, and change window.",
                "input_fields": "failure_rate, ci_tier, incident_load, change_window",
                "output_fields": "risk_score, risk_level, recommended_window"
            },
            {
                "id": "step_4", "title": "Notify CAB and update change record",
                "type": "notify", "tool": "slack.mcp",
                "description": "Send the risk assessment to the Change Advisory Board via Slack and update the change record with the risk score and recommendation.",
                "input_fields": "cab_channel, risk_summary, change_id",
                "output_fields": "notification_sent, change_record_updated"
            }
        ]
    }
}


async def extract_steps(prompt: str, file_content: str = None) -> dict:
    await asyncio.sleep(0.3)

    workflow_id = f"wf-{random.randint(10000, 99999)}"
    detected = detect_workflow(prompt)
    wf = WORKFLOW_STEPS.get(detected, WORKFLOW_STEPS["itsm_incident_triage_resolution"])

    return {
        "workflow_id": workflow_id,
        "workflow_name": wf["name"],
        "detected_workflow": detected,
        "steps": wf["steps"],
        "confidence": 0.97
    }


async def match_tools(steps: list) -> list:
    await asyncio.sleep(0.2)

    tool_map = {
        "step_1": {"tool": "github.fetch_incidents",        "tool_id": "github_mcp_fetch_incidents",  "type": "mcp",       "confidence": 0.99},
        "step_2": {"tool": "stackoverflow.search_fixes",    "tool_id": "stackoverflow_search_fixes",  "type": "open_api",  "confidence": 0.95},
        "step_3": {"tool": "weave.generate_resolution_plan",        "tool_id": "weave_resolution_plan_generator", "type": "generated", "confidence": 0.94}
    }

    matches = []
    for step in steps:
        step_id = step.get("id", "")
        match = tool_map.get(step_id, {
            "tool": "weave.generic",
            "tool_id": "weave_generic",
            "type": "generated",
            "confidence": 0.80
        })
        matches.append({"step_id": step_id, **match})

    return matches


async def edit_step(step: dict, instruction: str) -> dict:
    await asyncio.sleep(0.1)
    updated = dict(step)
    lc = instruction.lower()

    if "async" in lc:
        updated["description"] = "[async] " + updated.get("description", "")
        updated["type"] = "async"
    elif "retry" in lc or "error handling" in lc:
        updated["description"] += " Includes retry logic with exponential backoff on failure."
    elif "log" in lc:
        updated["description"] += " All inputs and outputs are logged for observability."
    elif "timeout" in lc:
        updated["description"] += " Request timeout enforced at 30s."
    elif "parallel" in lc:
        updated["description"] += " Runs in parallel with other steps where possible."
    else:
        updated["description"] = instruction.capitalize() + ". " + updated.get("description", "")

    return updated


async def generate_triage_script(incidents: list, so_results: dict) -> dict:
    await asyncio.sleep(0.2)

    script_code = '''"""
Weave-generated incident triage scoring script
Generated at: {timestamp}
Workflow: Incident Triage and Resolution
"""

def score_incident(incident, so_fix_available, so_score):
    score = 0
    labels = [l.lower() for l in incident.get("labels", [])]
    if "p1" in labels:
        score += 50
    elif "p2" in labels:
        score += 25
    hours_open = incident.get("hours_open", 0)
    score += min(30, hours_open * 2)
    if not so_fix_available:
        score += 15
    else:
        fix_confidence = min(10, so_score) / 10
        score += int((1 - fix_confidence) * 10)
    return min(100, score)

def triage(incident, so_results):
    inc_id = str(incident.get("number", ""))
    so = so_results.get(inc_id, {})
    so_fix = so.get("total_found", 0) > 0
    so_score = so.get("top_score", 0)
    triage_score = score_incident(incident, so_fix, so_score)
    resolution = "Immediate" if triage_score >= 70 else "Urgent" if triage_score >= 45 else "Standard"
    return {{
        "number": incident.get("number"),
        "title": incident.get("title"),
        "labels": incident.get("labels", []),
        "triage_score": triage_score,
        "resolution_priority": resolution,
        "fix_available": "Yes" if so_fix else "No",
        "top_fix_url": so.get("top_url", ""),
        "hours_open": incident.get("hours_open", 0)
    }}
'''.format(timestamp=datetime.now().isoformat())

    scored_incidents = []
    for inc in incidents:
        inc_id = str(inc.get("number", ""))
        so = so_results.get(inc_id, {})
        so_fix = so.get("total_found", 0) > 0
        so_score = so.get("top_score", 0)

        labels = [l.lower() for l in inc.get("labels", [])]
        score = 0
        if "p1" in labels: score += 50
        elif "p2" in labels: score += 25
        hours_open = inc.get("hours_open", 0)
        score += min(30, int(hours_open) * 2)
        if not so_fix: score += 15
        score = min(100, score)

        resolution = "Immediate" if score >= 70 else "Urgent" if score >= 45 else "Standard"

        scored_incidents.append({
            "number": inc.get("number"),
            "title": inc.get("title"),
            "labels": inc.get("labels", []),
            "triage_score": score,
            "resolution_priority": resolution,
            "fix_available": "Yes" if so_fix else "No",
            "top_fix_url": so.get("top_url", ""),
            "hours_open": hours_open,
            "assignment_group": inc.get("assignment_group", "Unassigned"),
            "url": inc.get("url", "")
        })

    scored_incidents.sort(key=lambda x: x["triage_score"], reverse=True)

    return {
        "script_code": script_code,
        "scored_incidents": scored_incidents,
        "triage_order": [i["number"] for i in scored_incidents]
    }


async def compose_briefing(scored_incidents: list, so_results: dict, workflow_id: str) -> dict:
    await asyncio.sleep(0.2)

    # Handle both single incident and list
    if isinstance(scored_incidents, list) and len(scored_incidents) > 0:
        inc = scored_incidents[0]
    elif isinstance(scored_incidents, dict):
        inc = scored_incidents
    else:
        inc = {}

    inc_id = str(inc.get("number", "unknown"))
    inc_title = inc.get("title", "Unknown incident")
    so = so_results.get(inc_id, {}) if isinstance(so_results, dict) else {}
    fix_url = inc.get("top_fix_url") or so.get("top_url", "")
    fix_available = inc.get("fix_available", "No")
    triage_score = inc.get("triage_score", 0)
    resolution_priority = inc.get("resolution_priority", "Standard")
    hours_open = inc.get("hours_open", 0)
    labels = inc.get("labels", [])
    owner = inc.get("assignment_group", "Unassigned")

    fix_section = f"**Recommended Fix:** {fix_url}" if fix_url else "**No known fix found on Stack Overflow** — escalate to senior engineer."

    escalation_required = fix_available == "No" and triage_score >= 70
    escalation_note = "\n\n⚠️ **Escalation Required:** This incident has no known fix and is high severity. Immediate senior engineering involvement recommended." if escalation_required else ""

    action_items_list = []
    if fix_url:
        action_items_list.append(f"Apply the recommended fix: {fix_url}")
    else:
        action_items_list.append("Escalate to senior engineer — no known fix found on Stack Overflow")
    action_items_list.append(f"Assign to {owner} for immediate action")
    action_items_list.append("Update incident status to In Progress")
    if triage_score >= 70:
        action_items_list.append("Notify on-call lead — this incident is high priority")

    resolution_plan = f"""## Resolution Plan — #{inc_id}: {inc_title}

**Generated by Jacquard Loom** | Workflow: {workflow_id} | {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

---

### Incident Summary
- **Issue:** #{inc_id} — {inc_title}
- **Labels:** {', '.join(labels) if labels else 'None'}
- **Triage Score:** {triage_score}/100
- **Resolution Priority:** {resolution_priority}
- **Time Open:** {hours_open}h
- **Assigned To:** {owner}
- **Known Fix Available:** {fix_available}

---

### Resolution Steps
{fix_section}

**Action Items:**
{chr(10).join(f"{i+1}. {item}" for i, item in enumerate(action_items_list))}
{escalation_note}

---

### Stack Overflow Match
{"Top answer: " + fix_url if fix_url else "No relevant Stack Overflow answers found for this incident pattern."}

---
*Resolution plan generated by Jacquard Loom. Review and approve before posting to GitHub.*
*Human-in-the-loop approval required before posting.*""".strip()

    return {
        "briefing": resolution_plan,
        "action_items": action_items_list,
        "escalations": [{
            "incident": f"#{inc_id} {inc_title[:60]}",
            "reason": "High severity with no known fix",
            "recommended_owner": owner
        }] if escalation_required else [],
        "summary": {
            "total": 1,
            "immediate": 1 if resolution_priority == "Immediate" else 0,
            "urgent": 1 if resolution_priority == "Urgent" else 0,
            "standard": 1 if resolution_priority == "Standard" else 0
        }
    }


async def generate_tool_schema(name: str, description: str, system: str, category: str) -> dict:
    await asyncio.sleep(0.6)
    slug = name.lower().replace(" ", "_").replace(".", "_")
    endpoint = f"/api/{system}/v1/{slug}"
    auth_key = (system.upper().replace(".", "_") + "_API_KEY")

    script_template = f'''async def execute(inputs: dict, config: dict) -> dict:
    """
    {description or f"Execute {name} operation on {system}."}
    """
    import httpx

    url     = config.get("endpoint", "{endpoint}")
    api_key = config.get("{auth_key}", "")
    headers = {{"Authorization": f"Bearer {{api_key}}"}} if api_key else {{}}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=inputs, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
'''

    return {
        "endpoint": endpoint,
        "inputs": ["record_id", "context", "options"],
        "outputs": ["result", "status", "metadata"],
        "description": description or f"Performs {name} operations on {system}.",
        "integration_type": "REST API",
        "auth_type": "api_key",
        "auth_key_name": auth_key,
        "script_template": script_template,
    }
