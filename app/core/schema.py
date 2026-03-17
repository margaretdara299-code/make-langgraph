"""
Database schema — all table definitions, indexes, and migrations.

Uses engine.raw_connection() for DDL since executescript is SQLite-specific.
Called once at application startup.
"""
from app.core.database import engine
from app.logger.logging import logger


def initialise_database() -> None:
    """Create all tables and indexes if they do not already exist."""
    logger.info("Initialising database schema...")
    raw_connection = engine.raw_connection()
    try:
        # 1. Check if skill table needs rebuild (simplified columns + is_active)
        skill_info = raw_connection.execute("PRAGMA table_info(skill);").fetchall()
        skill_column_names = {row[1] for row in skill_info}
        
        needs_skill_rebuild = bool(skill_info) and (
            "payer_id" in skill_column_names or 
            "owner_user_id" in skill_column_names or 
            "metadata_json" in skill_column_names or
            "token" in skill_column_names or
            "is_active" not in skill_column_names
        )

        if needs_skill_rebuild:
            logger.info("Rebuilding skill table: removing metadata_json/token and adding is_active...")
            raw_connection.executescript("""
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS skill_new;
                CREATE TABLE skill_new (
                  skill_id          TEXT PRIMARY KEY,
                  client_id         TEXT NOT NULL,
                  name              TEXT NOT NULL,
                  skill_key         TEXT NOT NULL,
                  description       TEXT,
                  category          TEXT,
                  is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                  created_by        TEXT NOT NULL DEFAULT '1',
                  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                  updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
                  UNIQUE (client_id, skill_key)
                );
                INSERT INTO skill_new (skill_id, client_id, name, skill_key, description, category, created_at, updated_at)
                SELECT skill_id, client_id, name, skill_key, description, category, created_at, updated_at
                FROM skill;
                DROP TABLE skill;
                ALTER TABLE skill_new RENAME TO skill;
                PRAGMA foreign_keys = ON;
            """)

        # 2. Check if skill_version table needs rebuild (enforce single version + defaults)
        sv_info = raw_connection.execute("PRAGMA table_info(skill_version);").fetchall()
        sv_column_names = {row[1] for row in sv_info}
        sv_indexes = raw_connection.execute("PRAGMA index_list(skill_version);").fetchall()
        has_unique_skill_id = any(idx[2] == 1 for idx in sv_indexes) 
        
        if bool(sv_info) and not has_unique_skill_id:
            logger.info("Rebuilding skill_version table to enforce defaults and single-version...")
            raw_connection.executescript("""
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS skill_version_new;
                CREATE TABLE skill_version_new (
                  skill_version_id    TEXT PRIMARY KEY,
                  skill_id            TEXT NOT NULL UNIQUE REFERENCES skill(skill_id) ON DELETE CASCADE,
                  environment         TEXT NOT NULL,
                  version             TEXT NOT NULL DEFAULT '1.0.1',
                  status              TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft','published')),
                  is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                  created_by          TEXT NOT NULL DEFAULT '1',
                  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
                  published_at        TEXT,
                  notes               TEXT,
                  compiled_skill_json TEXT,
                  compile_hash        TEXT,
                  nodes               TEXT NOT NULL DEFAULT '[]',
                  connections         TEXT NOT NULL DEFAULT '{}'
                );
                INSERT INTO skill_version_new (skill_version_id, skill_id, environment, version, status, is_active, created_at, nodes, connections)
                SELECT skill_version_id, skill_id, environment, '1.0.1', 'published', 1, created_at, nodes, connections
                FROM skill_version
                GROUP BY skill_id; 
                DROP TABLE skill_version;
                ALTER TABLE skill_version_new RENAME TO skill_version;
                PRAGMA foreign_keys = ON;
            """)

        # 3. Check if action_definition table needs rebuild (client_id default, status constraint)
        ad_info = raw_connection.execute("PRAGMA table_info(action_definition);").fetchall()
        ad_column_names = {row[1]: row for row in ad_info}
        
        ad_needs_rebuild = False
        if "client_id" in ad_column_names:
            client_id_row = ad_column_names["client_id"]
            # client_id_row format: (id, name, type, notnull, dflt_value, pk)
            if client_id_row[4] != "'1'" or client_id_row[3] == 0:
                ad_needs_rebuild = True

        if not ad_needs_rebuild:
            # Check for old status constraints just in case
            ad_master = raw_connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='action_definition'").fetchone()
            if ad_master and ("active','deprecated'" in ad_master[0]):
                ad_needs_rebuild = True

        if ad_needs_rebuild:
            logger.info("Rebuilding action_definition table: setting client_id default and fixing constraints...")
            raw_connection.executescript("""
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS action_definition_new;
                CREATE TABLE action_definition_new (
                  action_definition_id TEXT PRIMARY KEY,
                  action_key           TEXT NOT NULL UNIQUE,
                  name                 TEXT NOT NULL,
                  description          TEXT,
                  category             TEXT,
                  capability           TEXT,
                  icon                 TEXT,
                  default_node_title   TEXT,
                  scope                TEXT NOT NULL DEFAULT 'global'
                                       CHECK (scope IN ('global','client')),
                  client_id            TEXT NOT NULL DEFAULT '1',
                  status               TEXT NOT NULL DEFAULT 'published'
                                       CHECK (status IN ('draft','published')),
                  is_active            INTEGER NOT NULL DEFAULT 1
                                       CHECK (is_active IN (0,1)),
                  created_by           TEXT,
                  created_at           TEXT NOT NULL DEFAULT (datetime('now')),
                  updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO action_definition_new (
                    action_definition_id, action_key, name, description, category,
                    capability, icon, default_node_title, scope, client_id,
                    status, is_active, created_by, created_at, updated_at
                )
                SELECT 
                    action_definition_id, action_key, name, description, category,
                    capability, icon, default_node_title, scope, COALESCE(client_id, '1'),
                    status, is_active, created_by, created_at, updated_at
                FROM action_definition;
                DROP TABLE action_definition;
                ALTER TABLE action_definition_new RENAME TO action_definition;
                PRAGMA foreign_keys = ON;
            """)

        # 4. Create all tables with final definitions
        raw_connection.executescript("""
            CREATE TABLE IF NOT EXISTS skill (
              skill_id          TEXT PRIMARY KEY,
              client_id         TEXT NOT NULL,
              name              TEXT NOT NULL,
              skill_key         TEXT NOT NULL,
              description       TEXT,
              category          TEXT,
              is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
              created_by        TEXT NOT NULL DEFAULT '1',
              created_at        TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE (client_id, skill_key)
            );

            CREATE TABLE IF NOT EXISTS skill_version (
              skill_version_id    TEXT PRIMARY KEY,
              skill_id            TEXT NOT NULL UNIQUE REFERENCES skill(skill_id) ON DELETE CASCADE,
              environment         TEXT NOT NULL,
              version             TEXT NOT NULL DEFAULT '1.0.1',
              status              TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft','published')),
              is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
              created_by          TEXT NOT NULL DEFAULT '1',
              created_at          TEXT NOT NULL DEFAULT (datetime('now')),
              published_at        TEXT,
              notes               TEXT,
              compiled_skill_json TEXT,
              compile_hash        TEXT,
              nodes               TEXT NOT NULL DEFAULT '[]',
              connections         TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS skill_route (
              skill_route_id    TEXT PRIMARY KEY,
              skill_version_id  TEXT NOT NULL REFERENCES skill_version(skill_version_id) ON DELETE CASCADE,
              from_node_key     TEXT NOT NULL,
              to_node_key       TEXT NOT NULL,
              from_handle       TEXT,
              to_handle         TEXT,
              condition_json    TEXT NOT NULL DEFAULT '{}',
              is_default        INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1)),
              created_at        TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tag (
              tag_id      TEXT PRIMARY KEY,
              name        TEXT NOT NULL UNIQUE,
              created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS skill_tag (
              skill_id    TEXT NOT NULL REFERENCES skill(skill_id) ON DELETE CASCADE,
              tag_id      TEXT NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
              created_at  TEXT NOT NULL DEFAULT (datetime('now')),
              PRIMARY KEY (skill_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS action_definition (
              action_definition_id TEXT PRIMARY KEY,
              action_key           TEXT NOT NULL UNIQUE,
              name                 TEXT NOT NULL,
              description          TEXT,
              category             TEXT,
              capability           TEXT,
              icon                 TEXT,
              default_node_title   TEXT,
              scope                TEXT NOT NULL DEFAULT 'global'
                                   CHECK (scope IN ('global','client')),
              client_id            TEXT NOT NULL DEFAULT '1',
              status               TEXT NOT NULL DEFAULT 'published'
                                   CHECK (status IN ('draft','published')),
              is_active            INTEGER NOT NULL DEFAULT 1
                                   CHECK (is_active IN (0,1)),
              created_by           TEXT,
              created_at           TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS action_version (
              action_version_id    TEXT PRIMARY KEY,
              action_definition_id TEXT NOT NULL UNIQUE
                                   REFERENCES action_definition(action_definition_id) ON DELETE CASCADE,
              inputs_schema_json   TEXT NOT NULL DEFAULT '{}',
              execution_json       TEXT NOT NULL DEFAULT '{}',
              outputs_schema_json  TEXT NOT NULL DEFAULT '{}',
              configurations_json  TEXT NOT NULL DEFAULT '{}',
              ui_form_json         TEXT NOT NULL DEFAULT '{}',
              policy_json          TEXT NOT NULL DEFAULT '{}',
              created_at           TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

        # 5. Final indexes
        raw_connection.executescript("""
            CREATE INDEX IF NOT EXISTS idx_skill_version_skill ON skill_version(skill_id, environment, status);
            CREATE INDEX IF NOT EXISTS idx_skill_route_version ON skill_route(skill_version_id);
            CREATE INDEX IF NOT EXISTS idx_skill_tag_skill ON skill_tag(skill_id);
            CREATE INDEX IF NOT EXISTS idx_skill_tag_tag ON skill_tag(tag_id);
            CREATE INDEX IF NOT EXISTS idx_action_def_category ON action_definition(category, capability);
        """)

        raw_connection.commit()
        logger.info("Database schema initialised successfully.")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()
