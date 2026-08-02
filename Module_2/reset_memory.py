"""
reset_memory.py
Run this ONCE before re-running seed_memory.py, to clear out
duplicate/test data and start clean.

USAGE:
  1. Copy into your Module_2 folder (next to memory_engine.py).
  2. Run:  python reset_memory.py
  3. Then run:  python seed_memory.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM family_members")
conn.execute("DELETE FROM medications")
conn.execute("DELETE FROM important_dates")
conn.execute("DELETE FROM preferences")
conn.commit()
conn.close()

print("memory.db cleared. Now run: python seed_memory.py")