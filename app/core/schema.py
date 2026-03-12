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
        raw_connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS skill (
              skill_id          TEXT PRIMARY KEY,
              client_id         TEXT NOT NULL,
              name              TEXT NOT NULL,
              skill_key         TEXT NOT NULL,
              description       TEXT,
              created_by        TEXT NOT NULL,
              created_at        TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE (client_id, skill_key)
            );

            CREATE TABLE IF NOT EXISTS skill_version (
              skill_version_id    TEXT PRIMARY KEY,
              skill_id            TEXT NOT NULL REFERENCES skill(skill_id) ON DELETE CASCADE,
              environment         TEXT NOT NULL,
              version             TEXT NOT NULL,
              status              TEXT NOT NULL CHECK (status IN ('draft','published','archived')),
              is_active           INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
              created_by          TEXT NOT NULL,
              created_at          TEXT NOT NULL DEFAULT (datetime('now')),
              published_at        TEXT,
              notes               TEXT,
              compiled_skill_json TEXT,
              compile_hash        TEXT,
              nodes               TEXT NOT NULL DEFAULT '[]',
              connections         TEXT NOT NULL DEFAULT '{}',
              UNIQUE (skill_id, environment, version)
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

            CREATE INDEX IF NOT EXISTS idx_skill_version_skill
              ON skill_version(skill_id, environment, status);

            CREATE INDEX IF NOT EXISTS idx_skill_route_version
              ON skill_route(skill_version_id);
            CREATE INDEX IF NOT EXISTS idx_skill_route_from
              ON skill_route(skill_version_id, from_node_key);

            -- Tag tables
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

            CREATE INDEX IF NOT EXISTS idx_skill_tag_skill ON skill_tag(skill_id);
            CREATE INDEX IF NOT EXISTS idx_skill_tag_tag ON skill_tag(tag_id);

            -- Action Catalog tables
            CREATE TABLE IF NOT EXISTS action_definition (
              action_definition_id TEXT PRIMARY KEY,
              action_key        TEXT NOT NULL UNIQUE,
              name              TEXT NOT NULL,
              description       TEXT,
              category          TEXT,
              capability        TEXT NOT NULL,
              icon              TEXT,
              default_node_title TEXT NOT NULL,
              scope             TEXT NOT NULL DEFAULT 'global'
                                CHECK (scope IN ('global','client')),
              client_id         TEXT,
              status            TEXT NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active','deprecated','disabled')),
              created_by        TEXT,
              created_at        TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_action_def_category
              ON action_definition(category, capability);

            CREATE TABLE IF NOT EXISTS action_version (
              action_version_id   TEXT PRIMARY KEY,
              action_definition_id TEXT NOT NULL
                                   REFERENCES action_definition(action_definition_id) ON DELETE CASCADE,
              version             TEXT NOT NULL,
              status              TEXT NOT NULL
                                  CHECK (status IN ('draft','published','archived')),
              is_active           INTEGER NOT NULL DEFAULT 0
                                  CHECK (is_active IN (0,1)),
              inputs_schema_json  TEXT NOT NULL DEFAULT '{}',
              execution_json      TEXT NOT NULL DEFAULT '{}',
              outputs_schema_json TEXT NOT NULL DEFAULT '{}',
              ui_form_json        TEXT NOT NULL DEFAULT '{}',
              policy_json         TEXT NOT NULL DEFAULT '{}',
              created_by          TEXT,
              created_at          TEXT NOT NULL DEFAULT (datetime('now')),
              published_at        TEXT,
              UNIQUE (action_definition_id, version)
            );

            CREATE INDEX IF NOT EXISTS idx_action_version_def_status
              ON action_version(action_definition_id, status, is_active);


            """
        )

        # Safe column migrations for skill table
        column_names = set()
        for row in raw_connection.execute("PRAGMA table_info(skill);").fetchall():
            column_names.add(row[1])

        migrations = []
        if "payer_id" not in column_names:
            migrations.append("ALTER TABLE skill ADD COLUMN payer_id TEXT;")
        if "category" not in column_names:
            migrations.append("ALTER TABLE skill ADD COLUMN category TEXT;")
        if "owner_user_id" not in column_names:
            migrations.append("ALTER TABLE skill ADD COLUMN owner_user_id TEXT;")
        if "owner_team_id" not in column_names:
            migrations.append("ALTER TABLE skill ADD COLUMN owner_team_id TEXT;")
        if "metadata_json" not in column_names:
            migrations.append("ALTER TABLE skill ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';")

        for statement in migrations:
            raw_connection.execute(statement)

        raw_connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_name_scope "
            "ON skill(client_id, COALESCE(payer_id, ''), name);"
        )

        # Safe column migrations for action_version table
        av_column_names = set()
        for row in raw_connection.execute("PRAGMA table_info(action_version);").fetchall():
            av_column_names.add(row[1])

        if "configurations_json" not in av_column_names:
            raw_connection.execute(
                "ALTER TABLE action_version ADD COLUMN configurations_json TEXT NOT NULL DEFAULT '{}';"
            )

        raw_connection.commit()
        logger.info("Database schema initialised successfully.")

    finally:
        raw_connection.close()
