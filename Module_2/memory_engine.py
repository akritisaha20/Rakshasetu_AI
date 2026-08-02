"""
memory_engine.py
Module 2, Engine 3: Memory Engine

Stores and retrieves the information that makes RakshaSetu feel
personal rather than generic: family members, medication schedules,
important dates, and facts picked up from conversation.

Storage: SQLite (genuinely persists across restarts, no account needed).

Two tiers, as requested:
- LONG-TERM memory: family members, medication schedules, important
  dates, stated preferences -- things that rarely change, stored
  indefinitely.
- SHORT-TERM memory: the last N conversational exchanges, kept only
  briefly to give the Companion Engine recent context ("what did we
  just talk about"), not meant to accumulate forever.

Honest note on "extracting" facts from natural speech: real NLP-based
fact extraction needs a language model. This uses simple keyword/
pattern matching as a lightweight MVP stand-in -- documented clearly
so it's not mistaken for true natural-language understanding.
"""

import sqlite3
import os
import re
import time
from collections import deque

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")
SHORT_TERM_MAX_LEN = 10  # how many recent exchanges to keep in memory (RAM, not DB)


class MemoryEngine:
    def __init__(self):
        self._init_db()
        self.short_term = deque(maxlen=SHORT_TERM_MAX_LEN)

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, relation TEXT, visit_schedule TEXT,
                created_at INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, times TEXT, notes TEXT,
                created_at INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS important_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT, date_text TEXT,
                created_at INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER
            )
        """)
        conn.commit()
        conn.close()

    # ---- Long-term memory: writing ----

    def remember_family_member(self, name, relation, visit_schedule=None):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO family_members (name, relation, visit_schedule, created_at) VALUES (?, ?, ?, ?)",
            (name, relation, visit_schedule, int(time.time()))
        )
        conn.commit()
        conn.close()

    def remember_medication(self, name, times, notes=None):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO medications (name, times, notes, created_at) VALUES (?, ?, ?, ?)",
            (name, times, notes, int(time.time()))
        )
        conn.commit()
        conn.close()

    def remember_important_date(self, description, date_text):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO important_dates (description, date_text, created_at) VALUES (?, ?, ?)",
            (description, date_text, int(time.time()))
        )
        conn.commit()
        conn.close()

    def set_preference(self, key, value):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, int(time.time()))
        )
        conn.commit()
        conn.close()

    # ---- Long-term memory: reading ----

    def get_family_members(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT name, relation, visit_schedule FROM family_members").fetchall()
        conn.close()
        return [{"name": r[0], "relation": r[1], "visit_schedule": r[2]} for r in rows]

    def get_medications(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT name, times, notes FROM medications").fetchall()
        conn.close()
        return [{"name": r[0], "times": r[1], "notes": r[2]} for r in rows]

    def get_important_dates(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT description, date_text FROM important_dates").fetchall()
        conn.close()
        return [{"description": r[0], "date": r[1]} for r in rows]

    def get_preference(self, key, default=None):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default

    def get_all_preferences(self):
        """
        NEW: returns every stored preference as a list of plain values
        (e.g. ["Bhajans", "Morning tea", "Evening walk"]), suitable for
        rendering directly as tags on the dashboard's Memory screen.
        """
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT key, value FROM preferences ORDER BY updated_at").fetchall()
        conn.close()
        return [{"key": r[0], "value": r[1]} for r in rows]

    # ---- Short-term memory (conversation, kept in RAM only) ----

    def add_conversation_turn(self, speaker, text):
        self.short_term.append({"speaker": speaker, "text": text, "time": time.time()})

    def get_recent_conversation(self):
        return list(self.short_term)

    # ---- Lightweight fact extraction (MVP, pattern-based, NOT true NLP) ----

    def extract_and_remember(self, statement):
        """
        Looks for a small set of known patterns in a statement and
        stores them automatically. This is a lightweight, honest MVP --
        NOT a real language-understanding system. Real fact extraction
        would need an actual NLP/LLM pipeline.
        Returns a description of what (if anything) was remembered.
        """
        statement_lower = statement.lower()

        # Pattern: "my <relation> <name> visits every <day>"
        m = re.search(
            r"my (\w+) (\w+) visits (every \w+|on \w+|\w+ ?\w*)",
            statement_lower
        )
        if m:
            relation, name, schedule = m.groups()
            self.remember_family_member(name.capitalize(), relation, schedule)
            return f"Remembered: {name.capitalize()} ({relation}) visits {schedule}"

        # Pattern: "I take <medication> at <time>"
        m = re.search(r"i take (\w+) (?:at|every) ([\w: ]+)", statement_lower)
        if m:
            med_name, med_time = m.groups()
            self.remember_medication(med_name.capitalize(), med_time.strip())
            return f"Remembered: takes {med_name.capitalize()} at {med_time.strip()}"

        return None

    # ---- Context generation for the Companion Engine ----

    def get_context_summary(self):
        """
        Builds a plain-text summary of everything remembered, suitable
        for the Companion Engine to reference when generating replies.
        """
        family = self.get_family_members()
        meds = self.get_medications()
        dates = self.get_important_dates()

        lines = []
        if family:
            lines.append("Family: " + "; ".join(
                f"{f['name']} ({f['relation']}, visits {f['visit_schedule']})" for f in family
            ))
        if meds:
            lines.append("Medications: " + "; ".join(
                f"{m['name']} at {m['times']}" for m in meds
            ))
        if dates:
            lines.append("Important dates: " + "; ".join(
                f"{d['description']} on {d['date']}" for d in dates
            ))
        return "\n".join(lines) if lines else "No memories stored yet."
