import sqlite3
import os

db_path = "tensaw_skills_studio.sqlite"
if not os.path.exists(db_path):
    print("Database not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT skill_version_id FROM skill_version LIMIT 1;")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row[0]}")
    else:
        print("No versions found.")
    conn.close()
