"""
Seed demo data — populates the database with sample skills and actions for first-run.

Hybrid storage model:
  - Nodes: stored as JSON in skill_version.nodes
  - Edges: stored in skill_route table
  - Tags: stored in tag + skill_tag
"""
from app.core.database import engine
from app.common.utils import generate_unique_id, generate_utc_timestamp, serialise_json
from app.logger.logging import logger


def seed_demo_data() -> None:
    """Insert demo skills and actions if the database is empty. Uses raw_connection for batch inserts."""
    raw = engine.raw_connection()
    cursor = raw.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM skill")
        count = cursor.fetchone()[0]
        if count > 0:
            logger.info(f"Database already has {count} skills — skipping seed.")
            return

        logger.info("Seeding demo data...")
        timestamp = generate_utc_timestamp()

        # ── Categories ──────────────────────────────────────────────────────────
        category_map = {}
        categories = [
            {"old_id": "cat_ai", "name": "AI", "desc": "Artificial Intelligence & LLMs"},
            {"old_id": "cat_rules", "name": "Rules", "desc": "Business Logic & Routing"},
            {"old_id": "cat_human", "name": "Human", "desc": "Human-in-the-loop tasks"},
            {"old_id": "cat_tasks", "name": "Tasks", "desc": "Operational Task Management"},
            {"old_id": "cat_pm", "name": "PM", "desc": "Project Management Integration"},
            {"old_id": "cat_messaging", "name": "Messaging", "desc": "Communication Channels"},
            {"old_id": "cat_workflow", "name": "Workflow", "desc": "End-to-end Process Flows"},
        ]
        for cat in categories:
            cursor.execute(
                "INSERT INTO category (name, description) VALUES (?,?)",
                (cat["name"], cat["desc"])
            )
            category_map[cat["old_id"]] = cursor.lastrowid

        # ── Capabilities ────────────────────────────────────────────────────────
        capability_map = {}
        capabilities = [
            {"old_id": "cap_ai", "name": "AI", "desc": "LLM Inference & Processing"},
            {"old_id": "cap_rules", "name": "RULES", "desc": "Static & Dynamic Rule Execution"},
            {"old_id": "cap_human", "name": "HUMAN", "desc": "Manual Approval & Review"},
            {"old_id": "cap_api", "name": "API", "desc": "External System Integrations"},
            {"old_id": "cap_msg", "name": "MESSAGE", "desc": "Notification & Messaging"},
            {"old_id": "cap_workflow", "name": "Workflow", "desc": "Orchestration & State Management"},
        ]
        for cap in capabilities:
            cursor.execute(
                "INSERT INTO capability (name, description) VALUES (?,?)",
                (cap["name"], cap["desc"])
            )
            capability_map[cap["old_id"]] = cursor.lastrowid

        # ── Connectors ──────────────────────────────────────────────────────────
        connector_map = {}
        connectors = [
            {"old_id": "conn_primrose", "name": "Primrose Database", "type": "database", "desc": "Primrose Ops DB",
             "config": {
                 "host": "54.211.59.215",
                 "port": 3306,
                 "user": "af_user",
                 "password": "prim1615test",
                 "database": "alloFactorV4"
             }},
            {"old_id": "conn_trillium", "name": "Trillium Database", "type": "database", "desc": "Trillium Workflow DB",
             "config": {
                 "host": "54.211.59.215",
                 "port": 3306,
                 "user": "af_user",
                 "password": "prim1615test",
                 "database": "trillium_stage_workflow_v4"
             }},
            {"old_id": "conn_api_example", "name": "External API Service", "type": "api", "desc": "Configurable API Connector",
             "config": {
                 "method": "POST",
                 "url": "https://api.example.com/data",
                 "pathparam": {"id": "123"},
                 "queryparam": {"version": "v1"},
                 "bodyrequest": {"item": "sample"},
                 "header": {"Authorization": "Bearer ...", "Content-Type": "application/json"},
                 "response": {"status": "success", "data": {}}
             }},
            {"old_id": "conn_jira", "name": "Jira Product", "type": "api", "desc": "Company Jira instance", "config": {"url": "https://jira.company.com", "token": "tkn_12345"}},
            {"old_id": "conn_slack", "name": "Slack Operations", "type": "api", "desc": "Slack workspace for ops", "config": {"webhook_url": "https://hooks.slack.com/services/...", "token": "xoxb-..."}},
        ]
        for conn in connectors:
            cursor.execute(
                "INSERT INTO connector (name, connector_type, description, config_json, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (conn["name"], conn["type"], conn["desc"], serialise_json(conn["config"]), 1, timestamp, timestamp)
            )
            connector_map[conn["old_id"]] = cursor.lastrowid

        # ── Actions (MASTER DATA) ───────────────────────────────────────────────
        actions = [
            {
                "action_key": "ai.classify",
                "name": "AI Classify",
                "description": "LLM-based classification (category, intent, next-step suggestion)",
                "category_id": "cat_ai", "capability_id": "cap_ai", "icon": "brain",
                "default_node_title": "AI Classify",
                "inputs_schema": {"fields": [
                    {"name": "record_id", "type": "string", "required": True},
                    {"name": "text", "type": "string", "required": True},
                ]},
                "outputs_schema": {"fields": [
                    {"name": "label", "type": "string", "required": True},
                    {"name": "confidence", "type": "number", "required": True},
                ]},
                "execution": {"model": "gpt-4o", "temperature": 0.1, "max_tokens": 500},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": False}},
            },
            {
                "action_key": "rules.evaluate",
                "name": "Rules Engine",
                "description": "Rules-based decisioning and routing",
                "category_id": "cat_rules", "capability_id": "cap_rules", "icon": "git-branch",
                "default_node_title": "Rules Engine",
                "inputs_schema": {"fields": [{"name": "record_id", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "decision", "type": "string", "required": True}]},
                "execution": {"rule_set_id": "rs_default", "engine": "simple"},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "human.review",
                "name": "Human Review",
                "description": "Route to human reviewer for manual decision",
                "category_id": "cat_human", "capability_id": "cap_human", "icon": "user-check",
                "default_node_title": "Human Review",
                "inputs_schema": {"fields": [{"name": "record_id", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "decision", "type": "string", "required": True}]},
                "execution": {"queue": "human_review", "sla_hours": 24},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "task.create",
                "name": "Create Task",
                "description": "Create an operational task in a task system",
                "category_id": "cat_tasks", "capability_id": "cap_api", "icon": "clipboard-plus",
                "default_node_title": "Create Task",
                "inputs_schema": {"fields": [{"name": "record_id", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "task_id", "type": "string", "required": True}]},
                "execution": {"timeout_seconds": 30},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "pm.update",
                "name": "Update PM",
                "description": "Update a project-management item",
                "category_id": "cat_pm", "capability_id": "cap_api", "icon": "list-check",
                "default_node_title": "Update PM",
                "inputs_schema": {"fields": [{"name": "project_key", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "ok", "type": "boolean", "required": True}]},
                "execution": {"timeout_seconds": 30},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "message.send",
                "name": "Send Message",
                "description": "Send a message (email/sms/webhook)",
                "category_id": "cat_messaging", "capability_id": "cap_msg", "icon": "send",
                "default_node_title": "Send Message",
                "inputs_schema": {"fields": [{"name": "to", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "message_id", "type": "string", "required": True}]},
                "execution": {"channels": ["email", "sms", "webhook"], "retry_count": 3},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
        ]

        for action in actions:
            ad_id = generate_unique_id("ad_")
            av_id = generate_unique_id("av_")
            cat_id = category_map.get(action["category_id"])
            cap_id = capability_map.get(action["capability_id"])
            cursor.execute(
                "INSERT INTO action_definition (action_definition_id, action_key, name, description, category_id, capability_id, icon, default_node_title, scope, client_id, status, is_active, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ad_id, action["action_key"], action["name"], action["description"],
                 cat_id, cap_id, action["icon"], action["default_node_title"],
                 "global", "1", "published", 1, "system", timestamp, timestamp),
            )
            cursor.execute(
                "INSERT INTO action_version (action_version_id, action_definition_id, inputs_schema_json, execution_json, outputs_schema_json, policy_json) VALUES (?,?,?,?,?,?)",
                (av_id, ad_id,
                 serialise_json(action["inputs_schema"]), serialise_json(action["execution"]),
                 serialise_json(action["outputs_schema"]), serialise_json(action["policy"])),
            )

        # ── Skill + Version ─────────────────────────────────────────────────────
        demo_skill_id = generate_unique_id("skill_")
        demo_version_id = generate_unique_id("sv_")

        cursor.execute(
            "INSERT INTO skill (skill_id, client_id, name, skill_key, description, category_id, capability_id, is_active, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (demo_skill_id, "c_demo", "Ops Workflow Demo", "W01",
             "Demo: AI → Rules → Human → Task → PM → Message", 
             category_map.get("cat_workflow"), capability_map.get("cap_workflow"),
             1, "1", timestamp, timestamp),
        )

        # ── Nodes (JSON in skill_version.nodes) ─────────────────────────────────
        nodes_data = [
            {"id": "start", "type": "trigger.queue", "position": {"x": 120, "y": 160},
             "data": {"label": "Start", "description": "Entry trigger"}},
            {"id": "ai_classify", "type": "action.llm", "position": {"x": 320, "y": 160},
             "data": {"label": "AI Classify", "description": "LLM classification"}},
            {"id": "rules_engine", "type": "action.rules", "position": {"x": 520, "y": 160},
             "data": {"label": "Rules Engine", "description": "Rules-based decision"}},
            {"id": "human_review", "type": "action.human", "position": {"x": 720, "y": 160},
             "data": {"label": "Human Review", "description": "Manual decision"}},
            {"id": "create_task", "type": "action.api", "position": {"x": 920, "y": 160},
             "data": {"label": "Create Task", "description": "Create ops task"}},
            {"id": "update_pm", "type": "action.api", "position": {"x": 1120, "y": 160},
             "data": {"label": "Update PM", "description": "Update project mgmt item"}},
            {"id": "send_message", "type": "action.message", "position": {"x": 1320, "y": 160},
             "data": {"label": "Send Message", "description": "Notify stakeholders"}},
            {"id": "end", "type": "end.success", "position": {"x": 1520, "y": 160},
             "data": {"label": "End", "description": "Terminal"}},
        ]

        nodes_json = serialise_json(nodes_data)

        cursor.execute(
            "INSERT INTO skill_version (skill_version_id, skill_id, environment, version, status, is_active, created_by, created_at, nodes) VALUES (?,?,?,?,?,?,?,?,?)",
            (demo_version_id, demo_skill_id, "dev", "1.0.1", "published", 1, "1", timestamp, nodes_json),
        )

        # ── Edges (in skill_route table) ─────────────────────────────────────────
        edges = [
            ("start", "ai_classify"),
            ("ai_classify", "rules_engine"),
            ("rules_engine", "human_review"),
            ("human_review", "create_task"),
            ("create_task", "update_pm"),
            ("update_pm", "send_message"),
            ("send_message", "end"),
        ]

        for from_key, to_key in edges:
            edge_id = generate_unique_id("edge_")
            cursor.execute(
                "INSERT INTO skill_route (skill_route_id, skill_version_id, from_node_key, to_node_key, condition_json, is_default, created_at) VALUES (?,?,?,?,?,?,?)",
                (edge_id, demo_version_id, from_key, to_key, serialise_json({}), 1, timestamp),
            )

        # ── Tags (in tag + skill_tag) ────────────────────────────────────────────
        tag_demo_id = generate_unique_id("tag_")
        tag_auto_id = generate_unique_id("tag_")
        cursor.execute("INSERT INTO tag (tag_id, name) VALUES (?,?)", (tag_demo_id, "workflow-demo"))
        cursor.execute("INSERT INTO tag (tag_id, name) VALUES (?,?)", (tag_auto_id, "automation"))
        cursor.execute("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (?,?)", (demo_skill_id, tag_demo_id))
        cursor.execute("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (?,?)", (demo_skill_id, tag_auto_id))

        raw.commit()
        logger.info("Demo data seeded successfully (5 connectors, 6 actions, 1 skill, 7 edges, 2 tags).")

    finally:
        raw.close()