"""
test_hardware_bridge.py
Standalone test for the HardwareBridge -- uses FAKE/simulated state
transitions, so you can verify the hardware translation logic works
correctly WITHOUT needing real motors/OLED/speakers connected.
"""

from hardware_bridge import HardwareBridge

hw = HardwareBridge()

print("\n=== SCENARIO A: Normal conversation, robot tracking a person ===")
hw.enforce_hardware_profile("CONVERSATION", raw_left_pwm=80, raw_right_pwm=80)

print("\n=== SCENARIO B: Vision-Impaired accessibility mode (hazard nearby) ===")
hw.enforce_hardware_profile("ACCESSIBILITY", accessibility_mode="VISION_IMPAIRED",
                              raw_left_pwm=80, raw_right_pwm=80)
print("(Notice: motor power should be scaled down to 40% for careful movement)")

print("\n=== SCENARIO C: Hearing-Impaired accessibility mode (sign/gesture use) ===")
hw.enforce_hardware_profile("ACCESSIBILITY", accessibility_mode="HEARING_IMPAIRED",
                              raw_left_pwm=80, raw_right_pwm=80)

print("\n=== SCENARIO D: SAFETY ALERT triggered! ===")
hw.enforce_hardware_profile("SAFETY_ALERT", raw_left_pwm=80, raw_right_pwm=80)
print("(Notice: motors should hard-freeze to 0,0 regardless of requested speed)")
print("(You should also HEAR a siren tone through your speakers)")

print("\n=== SCENARIO D2: Speaking the 'Are you okay?' prompt (real audio) ===")
hw.speak("I noticed a sharp movement. Are you doing alright?")
print("(You should have HEARD this spoken through your speakers)")

print("\n=== SCENARIO E: Back to normal after alert clears ===")
hw.enforce_hardware_profile("CONVERSATION", raw_left_pwm=50, raw_right_pwm=50)

print("\nAll scenarios complete. Review the printed hardware commands above.")
hw.close()
