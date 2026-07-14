# RakshaSetu AI 🤖💙

**Companion. Accessible. Protective. One Robot, Always With Them.**

An AI-powered elder-care companion system that combines fall detection,
accessibility assistance, and emotional companionship into a single
integrated pipeline — built across 4 connected modules.

## The Problem

Elderly people living alone face several layered challenges:
- **Loneliness** — family lives far, daily check-ins get missed
- **Health/Medicine** — reminders forgotten, routines ignored
- **Sensory decline** — hearing/vision issues common with age
- **Silent physical risk** — falls are a leading cause of injury, often
  going undetected until it's too late

Most existing solutions solve these in isolation (a companion app OR
an accessibility tool OR a fall-detection wearable). RakshaSetu AI
combines all of it into one always-on system.

## Architecture — 5 Connected Modules

```
Module 1 (Perception)
   ↓ 15 FPS JSON telemetry over HTTP
Module 2 (Decision Layer) ── imported by both ──┐
   ↓                                             ↓
Module 3 (Hardware Bridge)              Module 4 (Cloud Backend)
                                                  ↓ web API
                                         Module 5 (Family Dashboard)
```

### Module 1 — Perception Layer
Captures live camera video and runs 4 AI pipelines in real time:
- **Fall detection** (MediaPipe Pose — velocity + posture-change analysis)
- **Gesture recognition** (MediaPipe Hands — Thumbs_Up, Thumbs_Down, Wave)
- **Distress tracking** (MediaPipe Face Mesh — a 0-10 pain_index)
- **Hazard detection** (YOLOv8-nano — objects in the person's path)

Outputs a standardized JSON packet, served over the network so other
modules can consume it live.

### Module 2 — Decision & Orchestration Layer
A finite state machine (Mode Manager) that reads Module 1's telemetry
and decides the robot's mode:
- **Conversation** — normal operation
- **Accessibility** — split into Vision-Impaired (hazard nearby) and
  Hearing-Impaired (sign/gesture use) sub-modes
- **Safety Alert** — triggered by a fall or sustained high distress

Includes a **Double-Verification loop**: rather than panicking at
every sudden movement, the system asks "Are you okay?" and waits for
a thumbs-up or response before escalating — reducing false alarms
while still catching real emergencies.

### Module 3 — Hardware Bridge
Translates decisions into physical actions: motor commands (with
Proportional Hardware Scaling — full speed normally, slower/careful
in Accessibility mode, hard-freeze in Safety Alert), OLED face
display states, and **real spoken audio** (text-to-speech) plus an
audible siren.

### Module 4 — Cloud Backend
Logs all telemetry to a local SQLite database, maintains a live
"digital twin" of the robot's status, and simulates a Dual-Path
Emergency Alert Gateway (push notification + voice call + SMS) for
when a real emergency is confirmed. Also serves this data over a
small web API so Module 5's dashboard can read it live.

### Module 5 — Family Dashboard
A single-page web dashboard (opened directly in a browser, no install
needed) that a family member checks to see how their loved one is
doing — in plain, reassuring language rather than raw data. Shows a
"presence" indicator that breathes calmly when all is well and pulses
red during a genuine alert, a plain-language status headline, and a
journal-style recent activity log. Reads live from Module 4's API.

## Current Status

| Module | Status |
|---|---|
| Module 1 (Perception) | ✅ Complete — tested live with real camera |
| Module 2 (Decision Logic) | ✅ Complete — tested with simulated + live data |
| Module 3 (Hardware Bridge) | ✅ Complete (simulated motors/OLED, **real audio**) |
| Module 4 (Cloud Backend) | ✅ Complete (real local DB, simulated Firebase/Twilio) |
| Module 5 (Family Dashboard) | ✅ Complete — tested live, updates correctly with real events |

**Known limitations:**
- Currently developed/tested on a laptop webcam (`camera_dev.py`);
  swapping to the real Raspberry Pi camera (`camera.py`) is a one-line
  change, documented in each module.
- Hazard detection currently recognizes `backpack`/`handbag` reliably
  (standard YOLO classes); `wire`/`shoes` would need a custom-trained
  model.
- Firebase and Twilio integrations in Module 4 are clearly-labeled
  simulations, since no cloud accounts are configured yet.
- Not yet deployed to physical Raspberry Pi + motor/OLED hardware.

## Running It

Each module has its own folder with a `requirements.txt` and a
`main.py`. General pattern:

```bash
cd Module_1
python -m venv venv
venv\Scripts\activate.bat        # Windows
pip install -r requirements.txt
python main.py
```

Module 1 must be running first (it serves the camera data), then
Module 3 and/or Module 4 can be started in separate terminals to
consume that data.

Each module also has a standalone test file (e.g.
`test_mode_manager.py`, `test_hardware_bridge.py`,
`test_cloud_backend.py`) that verifies the logic using simulated data,
without needing a camera at all.

## Tech Stack

- **Computer Vision:** OpenCV, MediaPipe (Pose/Hands/Face Mesh), YOLOv8-nano (Ultralytics)
- **Backend:** Python, Flask (Module 1 and Module 4's network servers), SQLite (Module 4's local logging)
- **Frontend:** HTML/CSS/JavaScript (Module 5's family dashboard)
- **Audio:** pyttsx3 (text-to-speech), winsound
- **Hardware (planned):** Raspberry Pi 4, Arduino/ESP32, L298N motor driver, OLED display

---

*Built as part of a hackathon project focused on affordable, integrated
elder-care technology.*