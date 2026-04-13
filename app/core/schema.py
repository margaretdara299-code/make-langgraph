"""
Database schema — all table definitions, indexes, and migrations.

Uses engine.raw_connection() for DDL since executescript is SQLite-specific.
Called once at application startup.
"""
from app.core.database import engine
from app.logger.logging import logger


def initialise_database() -> None:
    """Create all tables and indexes if they do not already exist."""
    logger.debug("Initialising database schema...")
    raw_connection = engine.raw_connection()
    try:
        # 0. Explicitly enable foreign keys for this connection
        raw_connection.execute("PRAGMA foreign_keys = ON;")

        # Create all tables with final definitions using INTEGER IDs
        raw_connection.executescript("""
            CREATE TABLE IF NOT EXISTS category (
              category_id INTEGER PRIMARY KEY AUTOINCREMENT,
              name        TEXT NOT NULL UNIQUE,
              description TEXT,
              created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS capability (
              capability_id INTEGER PRIMARY KEY AUTOINCREMENT,
              name          TEXT NOT NULL UNIQUE,
              description   TEXT,
              created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS connector (
              connector_id   INTEGER PRIMARY KEY AUTOINCREMENT,
              name           TEXT NOT NULL,
              connector_type TEXT NOT NULL,
              description    TEXT,
              config_json    TEXT NOT NULL DEFAULT '{}',
              status         TEXT NOT NULL DEFAULT 'active',
              is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
              created_at     TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS skill (
              skill_id          INTEGER PRIMARY KEY AUTOINCREMENT,
              client_id         INTEGER NOT NULL,
              name              TEXT NOT NULL,
              skill_key         TEXT NOT NULL,
              description       TEXT,
              category_id       INTEGER,
              capability_id     INTEGER,
              is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
              created_by        INTEGER NOT NULL DEFAULT 1,
              created_at        TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE (client_id, skill_key),
              FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE RESTRICT,
              FOREIGN KEY (capability_id) REFERENCES capability(capability_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS skill_version (
              skill_version_id    INTEGER PRIMARY KEY AUTOINCREMENT,
              skill_id            INTEGER NOT NULL,
              environment         TEXT NOT NULL,
              version             TEXT NOT NULL DEFAULT '1.0.1',
              status              TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft','published')),
              is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
              created_by          INTEGER NOT NULL DEFAULT 1,
              created_at          TEXT NOT NULL DEFAULT (datetime('now')),
              published_at        TEXT,
              notes               TEXT,
              compiled_skill_json TEXT,
              compile_hash        TEXT,
              nodes               TEXT NOT NULL DEFAULT '[]',
              connections         TEXT NOT NULL DEFAULT '{}',
              viewport_json       TEXT NOT NULL DEFAULT '{}',
              FOREIGN KEY (skill_id) REFERENCES skill(skill_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skill_route (
              skill_route_id    INTEGER PRIMARY KEY AUTOINCREMENT,
              skill_version_id  INTEGER NOT NULL,
              from_node_key     TEXT NOT NULL,
              to_node_key       TEXT NOT NULL,
              from_handle       TEXT,
              to_handle         TEXT,
              condition_json    TEXT NOT NULL DEFAULT '{}',
              is_default        INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1)),
              created_at        TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (skill_version_id) REFERENCES skill_version(skill_version_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tag (
              tag_id      INTEGER PRIMARY KEY AUTOINCREMENT,
              name        TEXT NOT NULL UNIQUE,
              created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS skill_tag (
              skill_id    INTEGER NOT NULL,
              tag_id      INTEGER NOT NULL,
              created_at  TEXT NOT NULL DEFAULT (datetime('now')),
              PRIMARY KEY (skill_id, tag_id),
              FOREIGN KEY (skill_id) REFERENCES skill(skill_id) ON DELETE CASCADE,
              FOREIGN KEY (tag_id) REFERENCES tag(tag_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS action_definition (
              action_definition_id INTEGER PRIMARY KEY AUTOINCREMENT,
              action_key           TEXT NOT NULL UNIQUE,
              name                 TEXT NOT NULL,
              description          TEXT,
              category_id          INTEGER,
              capability_id        INTEGER,
              icon                 TEXT,
              default_node_title   TEXT,
              scope                TEXT NOT NULL DEFAULT 'global'
                                   CHECK (scope IN ('global','client')),
              client_id            INTEGER NOT NULL DEFAULT 1,
              status               TEXT NOT NULL DEFAULT 'published'
                                   CHECK (status IN ('draft','published')),
              is_active            INTEGER NOT NULL DEFAULT 1
                                   CHECK (is_active IN (0,1)),
              created_by           INTEGER,
              created_at           TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at           TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE RESTRICT,
              FOREIGN KEY (capability_id) REFERENCES capability(capability_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS action_version (
              action_version_id    INTEGER PRIMARY KEY AUTOINCREMENT,
              action_definition_id INTEGER NOT NULL UNIQUE,
              inputs_schema_json   TEXT NOT NULL DEFAULT '{}',
              execution_json       TEXT NOT NULL DEFAULT '{}',
              outputs_schema_json  TEXT NOT NULL DEFAULT '{}',
              configurations_json  TEXT NOT NULL DEFAULT '{}',
              ui_form_json         TEXT NOT NULL DEFAULT '{}',
              policy_json          TEXT NOT NULL DEFAULT '{}',
              created_at           TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (action_definition_id) REFERENCES action_definition(action_definition_id) ON DELETE CASCADE
            );
        """)

        # 5. Final indexes
        raw_connection.executescript("""
            CREATE INDEX IF NOT EXISTS idx_skill_version_skill ON skill_version(skill_id, environment, status);
            CREATE INDEX IF NOT EXISTS idx_skill_route_version ON skill_route(skill_version_id);
            CREATE INDEX IF NOT EXISTS idx_skill_tag_skill ON skill_tag(skill_id);
            CREATE INDEX IF NOT EXISTS idx_skill_tag_tag ON skill_tag(tag_id);
            CREATE INDEX IF NOT EXISTS idx_action_def_category ON action_definition(category_id, capability_id);
        """)

        # 6. Seed Categories and Capabilities
        # Check if empty first
        count_cat = raw_connection.execute("SELECT COUNT(*) FROM category").fetchone()[0]
        if count_cat == 0:
            logger.debug("Seeding initial categories...")
            categories = [
                ("Eligibility", "Insurance verification"),
                ("Claims", "Claim processing and status"),
                ("Denials", "Denial management and appeals"),
                ("Clinical", "Medical records and charts"),
                ("AI/LLM", "Generative AI tasks"),
                ("Payments", "Financial transactions"),
                ("Workflow", "Routing and logic"),
                ("Messaging", "Notifications and alerts"),
                ("Analytics", "Data and reporting"),
                ("Compliance", "Regulatory and audit")
            ]
            raw_connection.executemany(
                "INSERT INTO category (name, description) VALUES (?, ?)", categories
            )

        count_cap = raw_connection.execute("SELECT COUNT(*) FROM capability").fetchone()[0]
        if count_cap == 0:
            logger.debug("Seeding initial capabilities...")
            capabilities = [
                ("Condition", "Evaluation and branching (IF/ELSE)"),
                ("Human", "Manual task for a person"),
                ("Agent", "Autonomous LLM reasoning"),
                ("HTTP", "External API call"),
                ("Function", "Specific code or tool execution"),
                ("Loop", "Iteration over a list"),
                ("Tool", "Pre-built utility"),
                ("Reply", "Send response to source"),
                ("Database", "SQL or NoSQL operations")
            ]
            raw_connection.executemany(
                "INSERT INTO capability (name, description) VALUES (?, ?)", capabilities
            )

        raw_connection.commit()
        logger.debug("Database schema initialised successfully.")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()



