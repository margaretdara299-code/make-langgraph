# Tensaw Skills Studio — Comprehensive API Documentation

**Version:** 0.5.0  
**Target Audience:** UI/UX Development Team  
**Base URL:** `http://localhost:8000`  
**Interactive Docs:** [Swagger UI](/docs) | [ReDoc](/redoc)

---

## 🏛️ System Architecture

The Tensaw Skills Studio API provides a backend for a visual workflow designer and management studio.
- **Taxonomy**: Hierarchy of Categories and Capabilities.
- **Connectors**: Credentials and configs for DBs, APIs, Slack, etc.
- **Actions**: Individual logic blocks (e.g., "AI Classify", "Send Slack").
- **Skills**: Versioned workflows represented as graphs of Nodes and Connections.

---

## 📡 Standard Communication Protocol

### Response Envelope
All responses return a JSON object with `status` and `message`.
```json
{
  "status": true,
  "message": "Human readable confirmation",
  "data": { ... payload here ... }
}
```

### Error Protocol
```json
{
  "status": false,
  "message": "Detailed error message",
  "data": null
}
```

---

## 🏗️ Module 1: Taxonomy & Health
**Base Prefix:** `/api/v1` (except Health)

### Endpoints Table
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | (Base `/`) Check API status |
| `GET` | `/categories` | List all categories |
| `POST` | `/categories` | Create a new category |
| `GET` | `/categories/{id}` | Get specific category |
| `PATCH` | `/categories/{id}` | Update category metadata |
| `DELETE` | `/categories/{id}` | Delete category |
| `GET` | `/capabilities` | List all capabilities |
| `POST` | `/capabilities` | Create a new capability |
| `GET` | `/capabilities/{id}` | Get specific capability |
| `PATCH` | `/capabilities/{id}` | Update capability metadata |
| `DELETE` | `/capabilities/{id}` | Delete capability |

### Real Data Samples
**Category List Item:**
```json
{ "category_id": 1, "name": "AI", "description": "Artificial Intelligence & LLMs" }
```

**Capability List Item:**
```json
{ "capability_id": 1, "name": "AI", "description": "LLM Inference & Processing" }
```

---

## 🔌 Module 2: Connectors
**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/connectors` | List all connectors. Optional: `?active_only=true` |
| `POST` | `/connectors` | Create a new integration |
| `GET` | `/connectors/{id}` | Get full connector config |
| `PATCH` | `/connectors/{id}` | Update config or status |
| `DELETE` | `/connectors/{id}` | Delete (only if unused) |

### Real Data Samples

**Database Connector (`connector_type: "database"`):**
```json
{
  "connector_id": 7,
  "name": "Primrose Database",
  "connector_type": "database",
  "config_json": {
    "host": "54.211.59.215",
    "port": 3306,
    "user": "af_user",
    "database": "alloFactorV4"
  },
  "status": "active"
}
```

**External API Connector (`connector_type: "api"`):**
```json
{
  "connector_id": 9,
  "name": "External API Service",
  "connector_type": "api",
  "config_json": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "header": { "Authorization": "Bearer ...", "Content-Type": "application/json" }
  }
}
```

---

## 🧩 Module 3: Action Catalog
**Base Prefix:** `/api`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/actions` | List actions. Filter: `?status=published&capability=1&q=search` |
| `POST` | `/actions` | Create a new action definition |
| `GET` | `/actions/{id}` | Get action detail (Includes logic schemas) |
| `PUT` | `/actions/{id}` | Update action definition and logic |
| `PUT` | `/actions/{id}/status` | Update only status (`draft`/`published`) |

### Real Data Samples

**Full Action Object (`GET /api/actions/ad_57ebee6a...`):**
```json
{
  "action_definition_id": "ad_57ebee6a-c87f-45b7-b70b-183ac6d53b65",
  "action_key": "ai.classify",
  "name": "AI Classify",
  "description": "LLM-based classification...",
  "status": "published",
  "inputs_schema_json": {
    "fields": [
      {"name": "record_id", "type": "string", "required": true},
      {"name": "text", "type": "string", "required": true}
    ]
  },
  "execution_json": {
    "model": "gpt-4o",
    "temperature": 0.1
  },
  "outputs_schema_json": {
    "fields": [
      {"name": "label", "type": "string", "required": true}
    ]
  }
}
```

---

## 🌪️ Module 4: Skills & Designer
**Base Prefix:** `/api`

### Endpoints Table
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **Library** | | |
| `GET` | `/skills` | List skills. Filter: `?client_id=...&search=...` |
| `POST` | `/skills` | Create a new top-level skill |
| `GET` | `/skills/{id}` | Get skill metadata & versions |
| `PATCH` | `/skills/{id}` | Update metadata (names, tags) |
| `DELETE` | `/skills/{id}` | Cascading delete of skill |
| **Designer** | | |
| `GET` | `/skills/versions/{sv_id}/graph` | Load Visual Graph (Nodes + Edges) |
| `GET` | `/skills/versions/{sv_id}` | Alias for graph + metadata |
| `PUT` | `/skills/versions/{sv_id}/graph` | Save entire graph layout |
| `PATCH` | `/skills/versions/{sv_id}/nodes/{node_id}/data` | Update single node state |
| **Lifecycle** | | |
| `POST` | `/skills/versions/{sv_id}/validate` | Check for broken links/cycles |
| `POST` | `/skills/versions/{sv_id}/compile` | Generate runnable JSON |
| `PUT` | `/skills/versions/{sv_id}/status` | Update status (`published` / `draft` / `unpublished`) |
| `POST` | `/skills/versions/{sv_id}/run` | Test run with input context |

### Real Data Samples

**Skill Version Detail (`GET /api/skills/versions/sv_399...`):**
```json
{
  "skill_version_id": "sv_39944f7f-0a4f-4ae3-9e18-c325c181eebe",
  "nodes": [
    {
      "id": "start",
      "type": "trigger.queue",
      "position": {"x": 120, "y": 160},
      "data": {"label": "Start"}
    },
    {
      "id": "ai_classify",
      "type": "action.llm",
      "position": {"x": 320, "y": 160},
      "data": {"label": "AI Classify"}
    }
  ],
  "connections": [
    {
      "id": "edge_1",
      "source": "start",
      "target": "ai_classify",
      "is_default": true
    }
  ]
}
```

**Run Skill Request:**
- `POST /api/skills/versions/{id}/run`
- **Body:** `{"input_context": {"claim_id": "999"}, "max_steps": 50}`

---

## 🚀 Error Registry

| Code | HTTP | Scenario |
| :--- | :--- | :--- |
| `BAD_REQUEST` | 400 | Invalid node type, missing connector, etc. |
| `NOT_FOUND` | 404 | Invalid skill_id or version_id |
| `CONFLICT` | 409 | Name/Key already exists |
| `INTERNAL_ERROR` | 500 | Unexpected backend crash |
