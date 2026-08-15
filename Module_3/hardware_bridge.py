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

# --- HC-SR04 ultrasonic distance sensor (real hardware, Raspberry Pi GPIO) ---
# SCAFFOLD ONLY: not yet wired up. TRIG_PIN/ECHO_PIN below are placeholders
# (BCM numbering) -- update once you know the real GPIO pins you're using.
# RPi.GPIO only imports successfully ON a real Raspberry Pi, so on your
# Windows dev laptop this always falls back to simulation automatically,
# same pattern as pyserial/pyttsx3/winsound above.
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

HC_SR04_TRIG_PIN = 23  # placeholder BCM pin -- update once wired
HC_SR04_ECHO_PIN = 24  # placeholder BCM pin -- update once wired

# --- OLED face display (real hardware, I2C) ---
# SCAFFOLD ONLY: not yet wired up, and exact panel model (SSD1306 vs SH1106,
# size) isn't confirmed yet. Defaults below assume the most common cheap
# option: a 0.96" 128x64 SSD1306 at I2C address 0x3C. If it turns out to be
# a different panel, only OLED_WIDTH/OLED_HEIGHT/OLED_I2C_ADDR and the
# adafruit_ssd1306 import below need to change -- the drawing logic
# (draw_face_*) stays the same.
try:
    import board
    import busio
    import adafruit_ssd1306
    from PIL import Image, ImageDraw, ImageFont
    OLED_AVAILABLE = True
except (ImportError, NotImplementedError):
    OLED_AVAILABLE = False

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_I2C_ADDR = 0x3C

# --- Obstacle avoidance thresholds (uses HC-SR04 distance reading) ---
# These only take effect once the HC-SR04 is actually wired up --
# read_distance_cm() returns None in simulation, and None always means
# "no obstacle data, don't touch the motor command."
OBSTACLE_STOP_CM = 15    # closer than this: block forward motion entirely
OBSTACLE_SLOW_CM = 40    # closer than this: half forward speed


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

        # HC-SR04 setup (real GPIO on Pi, simulation everywhere else)
        self.gpio_ready = False
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(HC_SR04_TRIG_PIN, GPIO.OUT)
                GPIO.setup(HC_SR04_ECHO_PIN, GPIO.IN)
                GPIO.output(HC_SR04_TRIG_PIN, False)
                self.gpio_ready = True
                print(f"[Hardware Bridge] HC-SR04 ready on TRIG={HC_SR04_TRIG_PIN}, "
                      f"ECHO={HC_SR04_ECHO_PIN} (BCM).")
            except Exception as e:
                print(f"[Hardware Bridge] HC-SR04 GPIO setup failed ({e}). "
                      f"Running in SIMULATION mode.")
        else:
            print("[Hardware Bridge] RPi.GPIO not available (not on a Pi, or not "
                  "installed). HC-SR04 readings will be SIMULATED.")

        # OLED setup (real I2C display on Pi, simulation/console everywhere else)
        self.oled = None
        if OLED_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.oled = adafruit_ssd1306.SSD1306_I2C(
                    OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_I2C_ADDR)
                self.oled.fill(0)
                self.oled.show()
                print(f"[Hardware Bridge] OLED ready at I2C address "
                      f"{hex(OLED_I2C_ADDR)} ({OLED_WIDTH}x{OLED_HEIGHT}).")
            except Exception as e:
                print(f"[Hardware Bridge] OLED init failed ({e}). "
                      f"Face display will be console-only.")
        else:
            print("[Hardware Bridge] adafruit_ssd1306/board/busio not available "
                  "(not on a Pi, or not installed). Face display will be console-only.")

    def read_distance_cm(self):
        """
        Reads a real distance in cm from the HC-SR04 (standard trig-pulse /
        echo-timing method). Returns None and prints a simulated reading
        message if no real sensor is connected -- callers should treat
        None as 'no hazard data available' rather than crashing.
        """
        if not self.gpio_ready:
            print("[HC-SR04 Simulation] No real sensor connected -- returning None.")
            return None

        try:
            import time as _time
            GPIO.output(HC_SR04_TRIG_PIN, True)
            _time.sleep(0.00001)  # 10 microsecond trigger pulse
            GPIO.output(HC_SR04_TRIG_PIN, False)

            timeout = _time.time() + 0.04  # 40ms timeout (~6.8m max range)
            pulse_start = _time.time()
            while GPIO.input(HC_SR04_ECHO_PIN) == 0:
                pulse_start = _time.time()
                if pulse_start > timeout:
                    return None

            pulse_end = _time.time()
            while GPIO.input(HC_SR04_ECHO_PIN) == 1:
                pulse_end = _time.time()
                if pulse_end > timeout:
                    return None

            duration = pulse_end - pulse_start
            distance_cm = (duration * 34300) / 2  # speed of sound = 343 m/s
            return round(distance_cm, 1)
        except Exception as e:
            print(f"[HC-SR04] Reading failed ({e}).")
            return None

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
        """
        Updates the OLED face display. Draws to the real I2C OLED when one
        is connected (self.oled set in __init__); always also prints to
        console so behavior/logging is unchanged when running in simulation.
        """
        if state_mode == "SAFETY_ALERT":
            label = "⚠️  CRITICAL ALERT ICON (Flashing Red/High Contrast)"
            oled_text = "!! ALERT !!"
        elif state_mode == "ACCESSIBILITY":
            if accessibility_mode == "VISION_IMPAIRED":
                label = "🔍 VISION-IMPAIRED MODE (Bold audio-guidance icons)"
                oled_text = "VISION MODE"
            elif accessibility_mode == "HEARING_IMPAIRED":
                label = "📝 HEARING-IMPAIRED MODE (Large text display)"
                oled_text = "HEARING MODE"
            else:
                label = "🔍 ACCESSIBILITY MODE (Enlarged UI)"
                oled_text = "ACCESS MODE"
        else:
            label = "😊 COMPANION SMILE (Blinking idle state)"
            oled_text = ":)"

        print(f"[OLED Face] Rendering: {label}")
        self._draw_on_oled(oled_text)

    def _draw_on_oled(self, text):
        """Pushes simple centered text to the real OLED, if one is connected.
        Placeholder rendering -- swap in real face icons/bitmaps once the
        actual panel and art assets are finalized."""
        if not self.oled:
            return
        try:
            image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(((OLED_WIDTH - text_w) // 2, (OLED_HEIGHT - text_h) // 2),
                       text, font=font, fill=255)
            self.oled.image(image)
            self.oled.show()
        except Exception as e:
            print(f"[OLED Face] (real display update failed: {e})")

    def trigger_audio_system(self, alert_active):
        """Controls audio output -- REAL siren sound through your speakers."""
        if alert_active:
            print("[Audio Out] 🔊 Outputting high-frequency local siren.")
            self.play_siren()
        else:
            print("[Audio Out] Audio channel set to idle/standard speech synthesis.")

    def _apply_obstacle_avoidance(self, left_pwm, right_pwm):
        """
        Reads the HC-SR04 and, if something is close ahead, clips or blocks
        FORWARD motor commands (reversing/turning is left alone, so the
        robot can still back away or turn out of a tight spot). Returns
        the (possibly adjusted) left/right PWM values.

        Does nothing while the sensor isn't wired up yet -- read_distance_cm()
        returns None in that case, which this treats as "no data, don't touch
        the command," so this stays a no-op until the real hardware is connected.
        """
        distance = self.read_distance_cm()
        if distance is None:
            return left_pwm, right_pwm

        if distance < OBSTACLE_STOP_CM:
            # Something is right in front -- block forward motion, but still
            # allow reversing/turning (negative or zero values pass through).
            new_left = left_pwm if left_pwm <= 0 else 0
            new_right = right_pwm if right_pwm <= 0 else 0
            if (new_left, new_right) != (left_pwm, right_pwm):
                print(f"[Obstacle Avoidance] {distance}cm ahead (< {OBSTACLE_STOP_CM}cm) "
                      f"-- blocking forward motion.")
            return new_left, new_right

        elif distance < OBSTACLE_SLOW_CM:
            # Getting close -- halve forward speed as a caution zone.
            new_left = int(left_pwm * 0.5) if left_pwm > 0 else left_pwm
            new_right = int(right_pwm * 0.5) if right_pwm > 0 else right_pwm
            if (new_left, new_right) != (left_pwm, right_pwm):
                print(f"[Obstacle Avoidance] {distance}cm ahead (< {OBSTACLE_SLOW_CM}cm) "
                      f"-- slowing forward motion.")
            return new_left, new_right

        return left_pwm, right_pwm

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
            scaled_left, scaled_right = self._apply_obstacle_avoidance(scaled_left, scaled_right)

            self.send_motor_command(scaled_left, scaled_right)
            self.update_face_display("ACCESSIBILITY", accessibility_mode)
            self.trigger_audio_system(alert_active=False)

        else:
            # Standard Operations: full baseline navigation flexibility,
            # still subject to obstacle avoidance
            safe_left, safe_right = self._apply_obstacle_avoidance(raw_left_pwm, raw_right_pwm)
            self.send_motor_command(safe_left, safe_right)
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
        if self.gpio_ready:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        if self.oled:
            try:
                self.oled.fill(0)
                self.oled.show()
            except Exception:
                pass
