"""
seed_memory.py
Run this ONCE to put some real data into Module_2's memory.db, so the
dashboard's Memory & Companion screen shows genuine data instead of
demo tags.

USAGE:
  1. Copy this file into your Module_2 folder (same folder as
     memory_engine.py).
  2. Run:  python seed_memory.py
  3. Edit the values below first to whatever's real for your demo.

Safe to run multiple times -- family/medication entries will just add
duplicates if you re-run it, so only run it once (or clear memory.db
first if you want to reset).
"""

from memory_engine import MemoryEngine

memory = MemoryEngine()

# --- Family members ---
memory.remember_family_member("Neha", "Daughter", "every Sunday")
memory.remember_family_member("Amit", "Son", "every second Saturday")

# --- Medications ---
memory.remember_medication("Metformin", "8:00 AM and 8:00 PM", notes="With food")
memory.remember_medication("Amlodipine", "9:00 AM")

# --- Important dates ---
memory.remember_important_date("Doctor visit", "Friday, August 7")
memory.remember_important_date("Neha's birthday", "September 12")

# --- Preferences ---
memory.set_preference("favorite_music", "Bhajans")
memory.set_preference("favorite_drink", "Morning tea")
memory.set_preference("favorite_activity", "Evening walk")

print("Seeded memory.db with:")
print(" Family:", memory.get_family_members())
print(" Medications:", memory.get_medications())
print(" Important dates:", memory.get_important_dates())
print(" Preferences:", memory.get_all_preferences())
