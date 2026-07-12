"""
hardware_bridge.py
Module 3: The Output & Actuation Layer (The Hardware Bridge)

Translates the abstract states from Module 2's ModeManager into actual
hardware commands: motor speeds (via serial to Arduino/ESP32), the OLED
face display, and audio output.

IMPORTANT: This gracefully SIMULATES motor/OLED hardware when none is
connected (prints clearly labeled messages instead), so you can test
and demo the logic on a laptop before wiring up the real Raspberry Pi +
Arduino + OLED. Once real hardware is connected, it automatically
switches to actually sending serial commands -- no code changes needed.

AUDIO IS REAL, NOT SIMULATED: uses your laptop's actual speakers via
text-to-speech (pyttsx3) and a real siren tone (winsound), since these
don't require any extra hardware beyond what your laptop already has.
"""

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False  # not on Windows (e.g. Raspberry Pi/Linux)


class HardwareBridge:
    def __init__(self, port='COM3', baudrate=115200):
        """
        port: on Windows this looks like 'COM3', 'COM4', etc.
              On Raspberry Pi/Linux it looks like '/dev/ttyUSB0'.
        If no hardware is connected (or pyserial isn't installed),
        this automatically falls back to simulation mode for motors/OLED.
        """
        self.serial_conn = None
        if SERIAL_AVAILABLE:
            try:
                self.serial_conn = serial.Serial(port, baudrate, timeout=0.1)
                print(f"[Hardware Bridge] Serial connection established on {port}")
            except Exception as e:
                print(f"[Hardware Bridge] No serial hardware found on {port} "
                      f"({e}). Running in SIMULATION mode.")
        else:
            print("[Hardware Bridge] pyserial not installed. Running in SIMULATION mode.")

        self.tts_engine = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 165)
                print("[Hardware Bridge] Text-to-speech ready (real audio via speakers).")
            except Exception as e:
                print(f"[Hardware Bridge] TTS init failed ({e}). Audio will be text-only.")
        else:
            print("[Hardware Bridge] pyttsx3 not installed. Audio will be text-only. "
                  "Install with: pip install pyttsx3")

    def speak(self, text):
        """Actually speaks the given text out loud through your laptop's speakers."""
        print(f"[Voice] \"{text}\"")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"[Voice] (TTS playback failed: {e})")

    def play_siren(self, duration_ms=300):
        """Plays a real audible alert tone through your laptop's speakers."""
        if WINSOUND_AVAILABLE:
            try:
                winsound.Beep(1500, duration_ms)
                winsound.Beep(1000, duration_ms)
            except Exception as e:
                print(f"[Audio] (Siren playback failed: {e})")
        else:
            print("[Audio] (Siren simulated -- winsound only available on Windows)")

    def send_motor_command(self, left_pwm, right_pwm):
        """
        Formats commands into the standardized low-level string:
        Format: M,<left_pwm>,<right_pwm>\\n
        """
        packet = f"M,{left_pwm},{right_pwm}\n"
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(packet.encode('utf-8'))
        else:
            print(f"[Motor Simulation] Would send: {packet.strip()}")

    def update_face_display(self, state_mode, accessibility_mode=None):
        """Updates the 1-inch OLED face display (simulated as console output for now)"""
        if state_mode == "SAFETY_ALERT":
            print("[OLED Face] Rendering: ⚠️  CRITICAL ALERT ICON (Flashing Red/High Contrast)")
        elif state_mode == "ACCESSIBILITY":
            if accessibility_mode == "VISION_IMPAIRED":
                print("[OLED Face] Rendering: 🔍 VISION-IMPAIRED MODE (Bold audio-guidance icons)")
            elif accessibility_mode == "HEARING_IMPAIRED":
                print("[OLED Face] Rendering: 📝 HEARING-IMPAIRED MODE (Large text display)")
            else:
                print("[OLED Face] Rendering: 🔍 ACCESSIBILITY MODE (Enlarged UI)")
        else:
            print("[OLED Face] Rendering: 😊 COMPANION SMILE (Blinking idle state)")

    def trigger_audio_system(self, alert_active):
        """Controls audio output -- REAL siren sound through your speakers."""
        if alert_active:
            print("[Audio Out] 🔊 Outputting high-frequency local siren.")
            self.play_siren()
        else:
            print("[Audio Out] Audio channel set to idle/standard speech synthesis.")

    def enforce_hardware_profile(self, active_state, accessibility_mode=None,
                                   raw_left_pwm=0, raw_right_pwm=0):
        """
        Applies Proportional Hardware Scaling based on the active state
        from Module 2's ModeManager. Call this whenever Module 2's state
        changes.
        """
        if active_state == "SAFETY_ALERT":
            # Immediate physical safety override: hard freeze
            self.send_motor_command(0, 0)
            self.update_face_display("SAFETY_ALERT")
            self.trigger_audio_system(alert_active=True)

        elif active_state == "ACCESSIBILITY":
            # Safety-first scaling: clip maximum power to 40% for smooth, careful approaches
            scaled_left = int(max(min(raw_left_pwm, 100), -100) * 0.4)
            scaled_right = int(max(min(raw_right_pwm, 100), -100) * 0.4)

            self.send_motor_command(scaled_left, scaled_right)
            self.update_face_display("ACCESSIBILITY", accessibility_mode)
            self.trigger_audio_system(alert_active=False)

        else:
            # Standard Operations: full baseline navigation flexibility
            self.send_motor_command(raw_left_pwm, raw_right_pwm)
            self.update_face_display("CONVERSATION")
            self.trigger_audio_system(alert_active=False)

    def close(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
