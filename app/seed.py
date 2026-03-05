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
    try:
        count = raw.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        if count > 0:
            logger.info(f"Database already has {count} skills — skipping seed.")
            return

        logger.info("Seeding demo data...")
        timestamp = generate_utc_timestamp()

        # ── Actions (MASTER DATA) ───────────────────────────────────────────────
        actions = [
            {
                "action_key": "ai.classify",
                "name": "AI Classify",
                "description": "LLM-based classification (category, intent, next-step suggestion)",
                "category": "AI", "capability": "AI", "icon": "brain",
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
                "category": "Rules", "capability": "RULES", "icon": "git-branch",
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
                "category": "Human", "capability": "HUMAN", "icon": "user-check",
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
                "category": "Tasks", "capability": "API", "icon": "clipboard-plus",
                "default_node_title": "Create Task",
                "inputs_schema": {"fields": [{"name": "record_id", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "task_id", "type": "string", "required": True}]},
                "execution": {"connector_type": "task_system", "timeout_seconds": 30},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "pm.update",
                "name": "Update PM",
                "description": "Update a project-management item",
                "category": "PM", "capability": "API", "icon": "list-check",
                "default_node_title": "Update PM",
                "inputs_schema": {"fields": [{"name": "project_key", "type": "string", "required": True}]},
                "outputs_schema": {"fields": [{"name": "ok", "type": "boolean", "required": True}]},
                "execution": {"connector_type": "pm_system", "timeout_seconds": 30},
                "policy": {"environment_availability": {"dev": True, "staging": True, "prod": True}},
            },
            {
                "action_key": "message.send",
                "name": "Send Message",
                "description": "Send a message (email/sms/webhook)",
                "category": "Messaging", "capability": "MESSAGE", "icon": "send",
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
            raw.execute(
                "INSERT INTO action_definition (action_definition_id, action_key, name, description, category, capability, icon, default_node_title, scope, status, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ad_id, action["action_key"], action["name"], action["description"],
                 action["category"], action["capability"], action["icon"], action["default_node_title"],
                 "global", "active", "system", timestamp, timestamp),
            )
            raw.execute(
                "INSERT INTO action_version (action_version_id, action_definition_id, version, status, is_active, inputs_schema_json, execution_json, outputs_schema_json, policy_json, created_by, created_at, published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (av_id, ad_id, "1.0.0", "published", 1,
                 serialise_json(action["inputs_schema"]), serialise_json(action["execution"]),
                 serialise_json(action["outputs_schema"]), serialise_json(action["policy"]),
                 "system", timestamp, timestamp),
            )

        # ── Skill + Version ─────────────────────────────────────────────────────
        demo_skill_id = generate_unique_id("skill_")
        demo_version_id = generate_unique_id("sv_")

        raw.execute(
            "INSERT INTO skill (skill_id, client_id, name, skill_key, description, category, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (demo_skill_id, "c_demo", "Ops Workflow Demo", "W01",
             "Demo: AI → Rules → Human → Task → PM → Message", "Workflow",
             "system", timestamp, timestamp),
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

        raw.execute(
            "INSERT INTO skill_version (skill_version_id, skill_id, environment, version, status, is_active, created_by, created_at, nodes) VALUES (?,?,?,?,?,?,?,?,?)",
            (demo_version_id, demo_skill_id, "dev", "0.1.0", "draft", 1, "system", timestamp, nodes_json),
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
            raw.execute(
                "INSERT INTO skill_route (skill_route_id, skill_version_id, from_node_key, to_node_key, condition_json, is_default, created_at) VALUES (?,?,?,?,?,?,?)",
                (edge_id, demo_version_id, from_key, to_key, serialise_json({}), 1, timestamp),
            )

        # ── Tags (in tag + skill_tag) ────────────────────────────────────────────
        tag_demo_id = generate_unique_id("tag_")
        tag_auto_id = generate_unique_id("tag_")
        raw.execute("INSERT INTO tag (tag_id, name) VALUES (?,?)", (tag_demo_id, "workflow-demo"))
        raw.execute("INSERT INTO tag (tag_id, name) VALUES (?,?)", (tag_auto_id, "automation"))
        raw.execute("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (?,?)", (demo_skill_id, tag_demo_id))
        raw.execute("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (?,?)", (demo_skill_id, tag_auto_id))

        raw.commit()
        logger.info("Demo data seeded successfully (6 actions, 1 skill, 7 edges, 2 tags).")

    finally:
        raw.close()