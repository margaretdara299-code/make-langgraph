# Tensaw Skills Studio — API Documentation

**Base URL:** `http://localhost:8000`
**Swagger Docs:** `http://localhost:8000/docs`

---

## How to Run

```bash
cd tensaw-skills-studio-api
python main.py
```

Server starts at `http://0.0.0.0:8000` with auto-reload enabled.

---

## Project Structure

```
app/
├── skill/              ← Skills Library (CRUD, tags, search)
│   ├── controller.py   ← POST /api/skills, GET /api/skills
│   ├── service.py
│   └── repository.py
├── skill_graph/        ← Skill Designer (graph, validate, compile, publish, run)
│   ├── controller.py   ← GET/PUT graph, validate, compile, publish, run
│   ├── service.py
│   └── repository.py
├── action/             ← Action Catalog
│   ├── controller.py   ← GET /api/actions, GET /api/designer/actions
│   └── repository.py
├── models/skill.py     ← Pydantic request/response schemas
├── core/
│   ├── schema.py       ← SQLite DDL (all tables)
│   ├── database.py     ← SQLAlchemy engine + session
│   └── config.py       ← Environment config
├── common/
│   ├── errors.py       ← Error codes + raise_http_error
│   └── utils.py        ← ID generation, timestamps, JSON helpers
└── seed.py             ← Demo data (runs on first startup)
```

---

## Database Tables

| Table | Purpose |
|---|---|
| `skill` | Skill metadata (name, key, category) |
| `skill_version` | Versioned skill (status, nodes JSON, compiled output) |
| `skill_route` | Edges/connections between nodes (source of truth) |
| `tag` | Tag master list |
| `skill_tag` | Skill ↔ Tag junction |
| `action_definition` | Action catalog master |
| `action_version` | Versioned action configs (inputs/outputs/execution) |

**Storage model (hybrid):**
- **Nodes** → JSON in `skill_version.nodes`
- **Edges** → rows in `skill_route` table
- **Tags** → rows in `tag` + `skill_tag`

---

## API Endpoints

### Health

#### `GET /health`
```json
// Response
{"ok": true, "time": "2026-03-05T10:30:00Z"}
```

---

### Skills Library

#### `POST /api/skills` — Create Skill

```json
// Request Body
{
  "client_id": "c_demo",
  "environment": "dev",
  "name": "Denial Triage",
  "skill_key": "D01",
  "description": "Auto-classify and route denial claims",
  "category": "RCM",
  "tags": ["denial", "automation"],
  "payer_id": null,
  "owner_user_id": "user_123",
  "owner_team_id": null,
  "start_from": {
    "mode": "blank"
  }
}
```

```json
// Response 201
{
  "skill": {
    "id": "skill_abc123",
    "name": "Denial Triage",
    "skill_key": "D01",
    "client_id": "c_demo"
  },
  "skill_version": {
    "id": "sv_xyz789",
    "version": "0.1.0",
    "status": "draft",
    "environment": "dev"
  },
  "designer_url": "/designer/sv_xyz789"
}
```

**Validations:**
- `name`: 3–80 characters, unique per client_id + payer_id scope
- `skill_key`: optional (auto-generated if omitted), pattern `^[A-Z][A-Z0-9]{1,7}$`
- `environment`: must be `dev`, `staging`, or `prod`
- `tags`: max 10, each max 24 chars
- `start_from.mode`: `blank` (default), `template`, or `clone`

**Errors:**
- `409` — Skill name already exists in scope
- `409` — Skill key already exists

---

#### `GET /api/skills` — List Skills

```
GET /api/skills
GET /api/skills?status=draft
GET /api/skills?search=denial
GET /api/skills?client_id=c_demo&status=published&search=triage
```

```json
// Response
{
  "items": [
    {
      "id": "skill_abc123",
      "client_id": "c_demo",
      "name": "Denial Triage",
      "skill_key": "D01",
      "description": "Auto-classify denial claims",
      "category": "RCM",
      "tags": ["denial", "automation"],
      "latest_version_id": "sv_xyz789",
      "version": "0.1.0",
      "status": "draft",
      "environment": "dev",
      "updated_at": "2026-03-05T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### Skill Graph (Designer)

#### `GET /api/skill-versions/{skill_version_id}/graph` — Load Graph

```json
// Response
{
  "skill_version_id": "sv_xyz789",
  "skill_id": "skill_abc123",
  "environment": "dev",
  "version": "0.1.0",
  "status": "draft",
  "nodes": [
    {
      "id": "start",
      "type": "trigger.queue",
      "position": {"x": 120, "y": 160},
      "data": {"label": "Start", "description": "Entry trigger"}
    },
    {
      "id": "classify",
      "type": "action.llm",
      "position": {"x": 320, "y": 160},
      "data": {"label": "AI Classify", "description": "LLM classification"}
    },
    {
      "id": "end",
      "type": "end.success",
      "position": {"x": 520, "y": 160},
      "data": {"label": "End"}
    }
  ],
  "connections": {
    "edge_001": {
      "id": "edge_001",
      "source": "start",
      "target": "classify",
      "sourceHandle": null,
      "targetHandle": null,
      "condition": {},
      "is_default": true
    },
    "edge_002": {
      "id": "edge_002",
      "source": "classify",
      "target": "end",
      "sourceHandle": null,
      "targetHandle": null,
      "condition": {},
      "is_default": true
    }
  }
}
```

**Node shape** (React Flow compatible):
| Field | Type | Description |
|---|---|---|
| `id` | string | Unique node identifier |
| `type` | string | Node type (e.g. `trigger.queue`, `action.llm`, `end.success`) |
| `position` | `{x, y}` | Canvas position |
| `data` | object | Node-specific data (label, description, config, mappings) |

**Connection shape:**
| Field | Type | Description |
|---|---|---|
| `id` | string | Unique edge identifier |
| `source` | string | Source node id |
| `target` | string | Target node id |
| `sourceHandle` | string? | Output handle name |
| `targetHandle` | string? | Input handle name |
| `condition` | object | Routing condition (for conditional edges) |
| `is_default` | boolean | Default route when no condition matches |

---

#### `PUT /api/skill-versions/{skill_version_id}/graph` — Save Graph

```json
// Request Body
{
  "nodes": [
    {"id": "start", "type": "trigger.queue", "position": {"x": 120, "y": 160}, "data": {"label": "Start"}},
    {"id": "classify", "type": "action.llm", "position": {"x": 320, "y": 160}, "data": {"label": "AI Classify"}},
    {"id": "review", "type": "action.human", "position": {"x": 520, "y": 160}, "data": {"label": "Human Review"}},
    {"id": "end", "type": "end.success", "position": {"x": 720, "y": 160}, "data": {"label": "End"}}
  ],
  "connections": {
    "edge_1": {"id": "edge_1", "source": "start", "target": "classify", "is_default": true},
    "edge_2": {"id": "edge_2", "source": "classify", "target": "review", "is_default": true},
    "edge_3": {"id": "edge_3", "source": "review", "target": "end", "is_default": true}
  }
}
```

**Behavior:**
- Saves nodes as JSON in `skill_version.nodes`
- Upserts edges into `skill_route` table
- Deletes any existing edges NOT in incoming connections (edge sync)
- Returns the full graph (same as GET)

**Validations:**
- Skill version must be `draft` (else `409`)
- All node ids must be unique
- All `source`/`target` must reference existing node ids

---

#### `PATCH /api/skill-versions/{skill_version_id}/nodes/{node_id}/data` — Update Node Data

```json
// Request Body
{
  "data": {
    "label": "Updated Label",
    "description": "New description",
    "input_mapping": {"record_id": "{{ctx.claim_id}}"}
  }
}
```

```json
// Response
{"ok": true}
```

---

#### `POST /api/skill-versions/{skill_version_id}/validate` — Validate Graph

No request body needed.

```json
// Response
{
  "valid": true,
  "errors": [],
  "warnings": ["Unreachable nodes: orphan_node"]
}
```

**Checks:**
- At least one node exists
- No duplicate node ids
- Exactly one `trigger.*` start node
- At least one `end.*` terminal node
- All edges reference existing nodes
- Reachability from trigger (warnings for unreachable)
- Multi-output nodes without default route (warning)

---

#### `POST /api/skill-versions/{skill_version_id}/compile` — Compile Graph

No request body needed. Must pass validation first.

```json
// Response
{
  "compile_hash": "4dc0ce4ed786...",
  "compiled_skill_json": {
    "schema_version": "1.0",
    "skill_version_id": "sv_xyz789",
    "skill_id": "skill_abc123",
    "environment": "dev",
    "version": "0.1.0",
    "entry_node_key": "start",
    "nodes": { ... },
    "edges": [ ... ]
  }
}
```

**Errors:**
- `422` — Validation failed (returns error list)

---

#### `POST /api/skill-versions/{skill_version_id}/publish` — Publish Version

```json
// Request Body (optional)
{"notes": "First production release"}
```

```json
// Response
{"ok": true, "status": "published", "published_at": "2026-03-05T10:30:00Z"}
```

**Requirements:** Must be `draft` status and have a compiled output.
**Side effect:** Deactivates any previously published version for the same skill + environment.

---

#### `POST /api/skill-versions/{skill_version_id}/run` — Dry Run

```json
// Request Body
{
  "input_context": {
    "record_id": "claim_001",
    "payer": "Aetna",
    "denial_code": "CO-16"
  },
  "max_steps": 50
}
```

```json
// Response
{
  "status": "succeeded",
  "visited": ["start", "classify", "review", "end"],
  "context": {"record_id": "claim_001", "payer": "Aetna"},
  "last_outputs": {}
}
```

**Possible statuses:** `succeeded`, `failed`, `stopped:no_outgoing_route`, `stopped:no_route_matched`, `failed:max_steps_exceeded`

---

### Action Catalog

#### `GET /api/actions` — List All Actions

```
GET /api/actions
GET /api/actions?capability=AI&category=AI&search=classify
```

```json
// Response
{
  "items": [
    {
      "action_definition_id": "ad_abc123",
      "action_key": "ai.classify",
      "name": "AI Classify",
      "category": "AI",
      "capability": "AI",
      "action_version_id": "av_xyz789",
      "version": "1.0.0",
      "version_status": "published"
    }
  ],
  "total": 6
}
```

---

#### `GET /api/designer/actions` — Designer Action Palette

```
GET /api/designer/actions?client_id=c_demo&environment=dev
GET /api/designer/actions?client_id=c_demo&environment=dev&capability=AI
```

Returns published + active actions filtered by environment policy, with parsed input/output schemas for the Designer right panel.

```json
// Response
{
  "items": [
    {
      "action_version_id": "av_xyz789",
      "action_key": "ai.classify",
      "name": "AI Classify",
      "category": "AI",
      "capability": "AI",
      "icon": "brain",
      "default_node_title": "AI Classify",
      "requires_connector_type": null,
      "inputs": [
        {"name": "record_id", "type": "string", "required": true},
        {"name": "text", "type": "string", "required": true}
      ],
      "outputs": [
        {"name": "label", "type": "string", "required": true},
        {"name": "confidence", "type": "number", "required": true}
      ]
    }
  ],
  "total": 6
}
```

---

## Node Types

| Type | Category | Description |
|---|---|---|
| `trigger.queue` | Trigger | Entry point — queue-based trigger |
| `action.llm` | Action | LLM/AI processing |
| `action.rules` | Action | Rules engine decisioning |
| `action.human` | Action | Human review / manual decision |
| `action.api` | Action | External API call (requires connector) |
| `action.message` | Action | Send message (email/sms/webhook) |
| `end.success` | Terminal | Successful completion |

---

## Error Codes

All errors follow this shape:

```json
{
  "success": false,
  "error": {
    "code": "SKILL_NAME_EXISTS",
    "message": "A skill with this name already exists in this scope"
  }
}
```

| HTTP | Code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Invalid payload, duplicate node ids, bad edge references |
| 404 | `NOT_FOUND` | Resource not found |
| 404 | `SKILL_VERSION_NOT_FOUND` | Skill version ID doesn't exist |
| 409 | `CONFLICT` | Generic conflict |
| 409 | `SKILL_NAME_EXISTS` | Duplicate skill name in scope |
| 409 | `SKILL_VERSION_NOT_DRAFT` | Trying to edit a non-draft version |
| 409 | `SKILL_VERSION_NOT_COMPILED` | Trying to publish without compiling |
| 422 | `SKILL_GRAPH_VALIDATION_FAILED` | Graph has validation errors |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server error |

---

## Environment Setup

**`.env` file:**
```env
TITLE=Tensaw Skills Studio API
VERSION=0.2.0
HOST=0.0.0.0
PORT=8000
RELOAD=true
CORS_ORIGINS=*
DB_PATH=tensaw_skills_studio.sqlite
DB_POOL_SIZE=5
```

**`.gitignore` additions:**
```
*.sqlite
*.sqlite-shm
*.sqlite-wal
__pycache__/
```
