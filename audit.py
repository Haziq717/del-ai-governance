"""Store metadata only, not the scenario, recommendations, or API key."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent / 'assessments.db'


def record_event(model, outcome, tools):
    assessment_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute('CREATE TABLE IF NOT EXISTS events '
                   '(id TEXT, timestamp TEXT, model TEXT, outcome TEXT, tools TEXT, policy_version TEXT)')
        db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)',
                   (assessment_id, timestamp, model, outcome, json.dumps(tools), '1.0'))
    return {'assessment_id': assessment_id, 'timestamp': timestamp, 'model': model, 'policy_version': '1.0'}
