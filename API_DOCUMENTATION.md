# Tensaw Skills Studio — Comprehensive API Documentation

**Version:** 0.7.0  
**Target Audience:** UI/UX Development Team  
**Base URL:** `http://localhost:8000`  
**Interactive Docs:** [Swagger UI](/docs) | [ReDoc](/redoc)

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

## 🏗️ Module 1: Taxonomy
**Base Prefix:** `/api/v1`

| Method | Endpoint | Description | Sample Request |
| :--- | :--- | :--- | :--- |
| `POST` | `/categories` | Create Category | `{"name": "AI", "description": "..."}` |
| `PATCH` | `/categories/{id}` | Update Category | `{"name": "AI Gen"}` |
| `POST` | `/capabilities` | Create Capability | `{"name": "LLM", "description": "..."}` |
| `PATCH` | `/capabilities/{id}` | Update Capability | `{"name": "NLP"}` |

### Samples:
**Create Category (`POST /categories`):**
```json
{
  "name": "Data Processing",
  "description": "Modules for ETL and data transformation"
}
```

**Update Category (`PATCH /categories/1`):**
```json
{
  "description": "Updated description for AI modules"
}
```

---

## 🔌 Module 2: Connectors
**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/connectors/connectivity/verify` | Verify credentials before saving |
| `POST` | `/connectors` | Save a new connector |
| `PATCH` | `/connectors/{id}` | Update existing connector |

### Samples:

**Verify Connectivity (`POST /connectors/connectivity/verify`):**
```json
{
  "engine": "mysql",
  "host": "54.211.59.215",
  "port": 3306,
  "username": "af_user",
  "password": "...",
  "database": "trilliumv1"
}
```

**Create Connector (`POST /connectors`):**
```json
{
  "name": "Production Postgres",
  "connector_type": "database",
  "config_json": {
    "engine": "postgresql",
    "host": "localhost",
    "port": 5432,
    "user": "root",
    "database": "main_db"
  }
}
```

---

## 🧩 Module 3: Action Catalog
**Base Prefix:** `/api`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/actions` | Create Action Definition |
| `PUT` | `/actions/{id}` | Update Full Definition |
| `PUT` | `/actions/{id}/status` | Change lifecycle status |

### Samples:

**Create Action (`POST /api/actions`):**
```json
{
  "name": "Email Sender",
  "action_key": "comm.send_email",
  "client_id": "1",
  "status": "draft"
}
```

**Update Action Logic (`PUT /api/actions/{id}`):**
```json
{
  "name": "Email Sender (Updated)",
  "description": "Send SMTP emails to customers",
  "inputs_schema_json": {
    "fields": [
      {"name": "to", "type": "string", "required": true},
      {"name": "subject", "type": "string", "required": true}
    ]
  },
  "execution_json": {
    "provider": "sendgrid",
    "template_id": "tpl_123"
  }
}
```

**Update Status (`PUT /api/actions/{id}/status`):**
```json
{
  "status": "published"
}
```

---

## 🌪️ Module 4: Skills & Designer
**Base Prefix:** `/api`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/skills` | Create Skill |
| `PATCH` | `/skills/{id}` | Update Metadata |
| `PUT` | `/skills/versions/{id}/graph` | Save Designer Layout |
| `PATCH` | `/skills/versions/{id}/nodes/{node_id}/data` | Update Node State |
| `POST` | `/skills/versions/{id}/validate` | Validate Graph |
| `POST` | `/skills/versions/{id}/compile` | Compile to Runnable |
| `PUT` | `/skills/versions/{id}/status` | Lifecycle Transition |
| `POST` | `/skills/versions/{id}/run` | Execute/Test Run |

### Samples:

**Create Skill (`POST /api/skills`):**
```json
{
  "name": "Invoice Processor",
  "client_id": "1",
  "environment": "dev",
  "start_from": {"mode": "blank"}
}
```

**Save Graph (`PUT /api/skills/versions/{id}/graph`):**
```json
{
  "nodes": [
    {"id": "n1", "type": "trigger", "position": {"x": 50, "y": 50}, "data": {"label": "Start"}}
  ],
  "connections": []
}
```

**Update Node Data (`PATCH /api/skills/versions/{id}/nodes/n1/data`):**
```json
{
  "label": "New Trigger Label",
  "config": {"topic": "invoices"}
}
```

**Compile Skill (`POST /api/skills/versions/{id}/compile`):**
```json
{} 
```

**Set Status (`PUT /api/skills/versions/{id}/status`):**
```json
{
  "status": "published",
  "notes": "Ready for production"
}
```

**Run Skill (`POST /api/skills/versions/{id}/run`):**
```json
{
  "input_context": {"invoice_id": "INV-101"},
  "max_steps": 20
}
```

---

## 🚀 Error Registry

| Scenario | HTTP | Message Example |
| :--- | :--- | :--- |
| **Validation Filter** | 422 | `field required`, `value is not a valid integer` |
| **Auth Failure** | 500 | `Connectivity failed: Access denied for user...` |
| **Not Found** | 404 | `Skill not found` |
| **Conflict** | 409 | `Action with key ai.sample already exists` |
