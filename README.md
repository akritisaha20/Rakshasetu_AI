# RakshaSetu AI 🤖💙

**Companion. Accessible. Protective. One Robot, Always With Them.**

An AI-powered elder-care companion system that combines fall detection,
accessibility assistance, personalized memory, routine learning, and
caregiver connectivity into a single integrated platform — built
across 5 connected modules.

## The Problem

Elderly people living alone face several layered challenges:
- **Loneliness** — family lives far, daily check-ins get missed
- **Health/Medicine** — reminders forgotten, routines ignored
- **Sensory decline** — hearing/vision issues common with age
- **Silent physical risk** — falls are a leading cause of injury, often
  going undetected until it's too late

Most existing solutions solve these in isolation (a companion app OR
an accessibility tool OR a fall-detection wearable). RakshaSetu AI
combines all of it into one always-on system that protects, assists,
remembers, and responds.

## Architecture — 5 Connected Modules

```
Module 1 (Perception)
   -> 15 FPS JSON telemetry over HTTP
Module 2 (Decision & Intelligence Layer -- 5 engines)
   ->                                             ->
Module 3 (Hardware Bridge)                Module 4 (Cloud Backend)
                                                  -> web API
                                         Module 5 (Caregiver App)
```

### Module 1 -- Perception Layer
Captures live camera video and runs 4 AI pipelines in real time:
- **Fall detection** (MediaPipe Pose -- velocity + posture-change analysis)
- **Gesture recognition** (MediaPipe Hands -- Thumbs_Up, Thumbs_Down, Wave)
- **Distress tracking** (MediaPipe Face Mesh -- a 0-10 pain_index)
- **Hazard detection** (YOLOv8-nano -- objects in the person's path)

Outputs a standardized JSON packet, served over the network so other
modules can consume it live. Optimized with frame-skipping on the
expensive hazard detector and a lightweight pose model for better
performance on resource-limited hardware like a Raspberry Pi.

### Module 2 -- Decision & Intelligence Layer
A **Central Decision Manager** coordinating 5 interconnected engines,
with a strict priority hierarchy: **Safety always wins** over
conversation or routine interaction.

- **Safety Engine** -- fall detection, Double-Verification loop (asks
  "Are you okay?" and waits for confirmation before escalating,
  preventing false alarms from routine movements), sustained-distress
  escalation.
- **Accessibility Adaptation Engine** -- a persistent profile (hearing/
  vision impaired, dyslexia, mobility challenges) that adapts runtime
  behavior (speed, voice vs. visual output, text size), working
  alongside Module 1's real-time Vision/Hearing-Impaired detection.
- **Memory Engine** -- real SQLite-backed storage for family members,
  medication schedules, important dates, and user preferences, with
  lightweight pattern-based fact extraction from natural statements
  (e.g. "My daughter Neha visits every Sunday").
- **Routine Learning & Wellness Engine** -- learns a daily activity
  baseline over time and flags meaningful drops (a possible early
  signal of mobility decline), tracks wake/interaction patterns, and
  genuinely tracks **medication adherence** (taken vs. scheduled).
- **Companion AI Engine** -- rule-based, memory-aware supportive
  responses (e.g. referencing a family member by name, offering a
  voice message when the user says they miss someone).

### Module 3 -- Hardware Bridge
Translates decisions into physical actions: motor commands (with
Proportional Hardware Scaling -- full speed normally, slower/careful
in Accessibility mode, hard-freeze in Safety Alert), OLED face
display states (including a dedicated Medicine Reminder expression),
and **real spoken audio** (personalized text-to-speech using the
user's stored name) plus an audible siren. NodeMCU (ESP8266) firmware
included for driving real motors through an L298N motor driver.

### Module 4 -- Cloud Backend
Logs all telemetry to a local SQLite database, maintains a live
"digital twin" of the robot's status, generates weekly/monthly
caregiver reports from real logged data, and simulates a Dual-Path
Emergency Alert Gateway (push notification + voice call + SMS).
Serves all of this over a small web API for Module 5 to consume.

### Module 5 -- Caregiver App
A full multi-screen web dashboard (sidebar navigation, no install
needed) giving family members genuine visibility and connection:
- **Home Dashboard** -- elder status, battery, live activity feed
- **Safety Monitor** -- fall/hazard status and a detailed timeline
- **Wellness & Analytics** -- activity/mood/routine scores, real
  medication adherence percentage, activity trend chart
- **Memory & Companion** -- known preferences, family directory,
  active reminders (with a "mark as taken" control)
- **Family Connect** -- **real** voice message recording and playback
  via the browser's microphone, plus simulated video/phone call
  controls (honestly labeled as simulated, since routing to actual
  robot hardware audio isn't built yet)
- **Daily AI Summary** -- an automatically generated day-in-review
- **Emergency overlay** -- full-screen alert with live view, call, and
  emergency contact actions, triggered automatically on a real
  Safety Alert or manually via a demo button

## Current Status

| Module | Status |
|---|---|
| Module 1 (Perception) | Complete -- tested live with real camera |
| Module 2 (Decision & Intelligence, 5 engines) | Complete -- all engines tested, integrated into live pipeline |
| Module 3 (Hardware Bridge) | Complete (simulated motors/OLED, real audio), NodeMCU firmware written |
| Module 4 (Cloud Backend) | Complete (real local DB, simulated Firebase/Twilio, real weekly/monthly reports) |
| Module 5 (Caregiver App) | Complete -- full dashboard tested live, real mic recording/playback |

**Known limitations, stated honestly:**
- Currently developed/tested on a laptop webcam (`camera_dev.py`);
  swapping to the real Raspberry Pi camera (`camera.py`) is a one-line
  change, documented in the deployment guide.
- Hazard detection currently recognizes `backpack`/`handbag` reliably
  (standard YOLO classes); `wire`/`shoes` would need a custom-trained
  model.
- Firebase and Twilio integrations in Module 4 are clearly-labeled
  simulations, since no cloud accounts are configured yet.
- Memory Engine's fact extraction and Companion Engine's responses are
  lightweight, rule-based MVPs -- not a true language model. Documented
  clearly in code comments so this isn't mistaken for real NLP.
- Family Connect's video/phone call features are simulated states, not
  real WebRTC/telephony connections. Voice recording/playback itself
  is genuinely functional.
- NodeMCU motor controller firmware is written but not yet verified
  with real motors/hardware.
- Not yet deployed to physical Raspberry Pi + motor/OLED hardware.

## Running It

```bash
cd Raksha_AI
python -m venv rakshasetu_env
rakshasetu_env\Scripts\activate.bat   # Windows
pip install -r Module_1/requirements.txt
pip install flask requests pyttsx3
python run_all.py
```

This single script runs Modules 1-4 together. Then open
`Module_5/dashboard.html` in a browser (or serve it via
`python -m http.server 8000` in the `Module_5` folder, for microphone
access to work correctly in some browsers).

Each module also has standalone test files (e.g. `test_mode_manager.py`,
`test_hardware_bridge.py`, `test_cloud_backend.py`,
`test_decision_manager.py`) that verify logic using simulated data,
without needing a camera at all.

## Tech Stack

- **Computer Vision:** OpenCV, MediaPipe (Pose/Hands/Face Mesh), YOLOv8-nano (Ultralytics)
- **Backend:** Python, Flask, SQLite (Memory, Wellness, and Cloud logging)
- **Frontend:** HTML/CSS/JavaScript (Module 5's caregiver dashboard, including MediaRecorder for real voice messages)
- **Audio:** pyttsx3 (text-to-speech), winsound
- **Hardware:** Raspberry Pi 4/5, NodeMCU (ESP8266), L298N motor driver, OLED display

---

*Built as part of a hackathon/academic project focused on affordable,
integrated elder-care technology.*