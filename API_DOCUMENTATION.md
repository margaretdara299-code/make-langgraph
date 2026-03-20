# Tensaw Skills Studio — Comprehensive API Documentation

**Version:** 0.8.0  
**Target Audience:** UI/UX Development Team  
**Base URL:** `http://localhost:8000`  
**Interactive Docs:** [Swagger UI](/docs) | [ReDoc](/redoc)

---

## 📡 Standard Communication Protocol

### Response Envelope
All responses return a JSON object with `status`, `message`, and `data`.
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

## 🏗️ Module 1: Taxonomy
**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/categories` | List all categories |
| `POST` | `/categories` | Create Category |
| `GET` | `/categories/{id}` | Get Category details |
| `PATCH` | `/categories/{id}` | Update Category |
| `DELETE` | `/categories/{id}` | Delete Category |
| `GET` | `/capabilities` | List all capabilities |
| `POST` | `/capabilities` | Create Capability |
| `GET` | `/capabilities/{id}` | Get Capability details |
| `PATCH` | `/capabilities/{id}` | Update Capability |
| `DELETE` | `/capabilities/{id}` | Delete Capability |

### Samples:
**Create Category (`POST /v1/categories`):**
```json
{
  "name": "AI Services",
  "description": "Modules for LLM and predictive analytics"
}
```

**Get Categories (`GET /v1/categories`):**
```json
{
  "status": true,
  "message": "Categories fetched",
  "data": [
    {"category_id": 1, "name": "AI Services", "description": "...", "created_at": "..."}
  ]
}
```

---

## 🔌 Module 2: Connectors
**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/connectors` | List all connectors |
| `POST` | `/connectors` | Save a new connector |
| `GET` | `/connectors/{id}` | Get Connector details |
| `PATCH` | `/connectors/{id}` | Update connector |
| `DELETE` | `/connectors/{id}` | Delete connector |
| `GET` | `/connectors/grouped` | Get connectors grouped by type |
| `POST` | `/connectors/connectivity/verify` | Verify DB credentials |

### Samples:

**Verify Connectivity (`POST /v1/connectors/connectivity/verify`):**
```json
{
  "engine": "mysql",
  "host": "127.0.0.1",
  "port": 3306,
  "username": "root",
  "password": "password",
  "database": "prod_db"
}
```

**Create Connector (`POST /v1/connectors`):**
```json
{
  "name": "Main SQL Engine",
  "connector_type": "database",
  "description": "Primary healthcare database",
  "config_json": {
    "engine": "postgresql",
    "host": "db.internal.local",
    "port": 5432,
    "user": "orchestrator",
    "database": "rcm_prod"
  }
}
```

---

## 🧩 Module 3: Action Catalog
**Base Prefix:** `/api`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/actions` | List all action definitions |
| `GET` | `/actions/grouped` | Get actions grouped by category |
| `POST` | `/actions` | Create Action Definition |
| `GET` | `/actions/{id}` | Get Full Definition + Logic |
| `PUT` | `/actions/{id}` | Update Full Definition |
| `PUT` | `/actions/{id}/status` | Change lifecycle status |
| `DELETE` | `/actions/{id}` | Delete Action |

### Samples:

**Grouped Actions (`GET /api/actions/grouped`):**
```json
{
  "status": true,
  "message": "Grouped actions fetched",
  "data": {
    "Eligibility": [
      {"action_definition_id": "uuid", "name": "Verify Eligibility", "action_key": "rcm.eligibility", "icon": "activity"}
    ],
    "Uncategorized": []
  }
}
```

**Create Action (`POST /api/actions`):**
```json
{
  "name": "Claim Scrubber",
  "action_key": "rcm.scrub_claim",
  "description": "Validate claims against payer rules",
  "category_id": 2,
  "capability_id": 5,
  "status": "published",
  "inputs_schema_json": {"properties": {"claim_id": {"type": "string"}}},
  "execution_json": {"provider": "rules-engine", "version": "2.0"}
}
```

---

## 🌪️ Module 4: Skills & Designer
**Base Prefix:** `/api`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/skills` | List all skill metadata |
| `POST` | `/skills` | Create Skill (Init version) |
| `GET` | `/skills/{id}` | Get Skill metadata |
| `PATCH` | `/skills/{id}` | Update Skill metadata |
| `DELETE` | `/skills/{id}` | Delete Skill + Versions |
| `GET` | `/skills/versions/{vid}/graph` | Load Nodes & Connections |
| `PUT` | `/skills/versions/{vid}/graph` | Save Bulk Layout |
| `PATCH` | `/skills/versions/{vid}/nodes/{nid}/data` | Update single node state |
| `POST` | `/skills/versions/{vid}/validate` | Validate graph integrity |
| `POST` | `/skills/versions/{vid}/compile` | Convert to Runnable JSON |
| `PUT` | `/skills/versions/{vid}/status` | Publish/Draft lifecycle |
| `POST` | `/skills/versions/{vid}/run` | Execute/Test runnable |

### Samples:

**Load Graph (`GET /api/skills/versions/{id}/graph`):**
```json
{
  "status": true,
  "message": "Graph loaded",
  "data": {
    "nodes": [
      {"id": "n1", "type": "trigger", "position": {"x": 10, "y": 10}, "data": {"label": "Start"}}
    ],
    "connections": {
      "e1": {"id": "e1", "source": "n1", "target": "n2"}
    }
  }
}
```

**Save Graph (`PUT /api/skills/versions/{id}/graph`):**
```json
{
  "nodes": [
    {"id": "n1", "type": "trigger", "position": {"x": 50, "y": 50}, "data": {"label": "Start"}},
    {"id": "n2", "type": "action.rcm", "position": {"x": 300, "y": 50}, "data": {"label": "Process"}}
  ],
  "connections": {
    "e1": {"id": "e1", "source": "n1", "target": "n2"}
  }
}
```

**Run Skill (`POST /api/skills/versions/{id}/run`):**
```json
{
  "input_context": {"patient_id": "P-9988"},
  "max_steps": 25
}
```

---

## 🚀 Error Registry

| Scenario | HTTP | Message Example |
| :--- | :--- | :--- |
| **Validation Filter** | 422 | `field required`, `value is not a valid integer` |
| **Auth/Connectivity** | 500 | `Connectivity failed: Access denied...` |
| **Not Found** | 404 | `Skill not found`, `Action not found` |
| **In Use Error** | 400 | `Action cannot be deleted: it is currently referenced...` |
| **Conflict** | 409 | `Action with key already exists` |
