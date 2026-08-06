/*
  motor_controller.ino
  FOR: NodeMCU (ESP8266)

  Receives serial commands from the Raspberry Pi (sent by hardware_bridge.py)
  and drives two motors via an L298N motor driver.

  Expected serial format (matches hardware_bridge.py exactly):
      M,<left_pwm>,<right_pwm>\n
  Example:
      M,60,60      -> both motors forward at 60% speed
      M,-60,-60    -> both motors backward at 60% speed
      M,0,0        -> stop (used automatically during Safety Alert)
      M,30,-30     -> turn in place (left forward, right backward)

  ============ WIRING (L298N to NodeMCU) ============
  L298N ENA  -> NodeMCU D1  (PWM, controls LEFT motor speed)
  L298N IN1  -> NodeMCU D2  (LEFT motor direction)
  L298N IN2  -> NodeMCU D3  (LEFT motor direction)
  L298N ENB  -> NodeMCU D5  (PWM, controls RIGHT motor speed)
  L298N IN3  -> NodeMCU D6  (RIGHT motor direction)
  L298N IN4  -> NodeMCU D7  (RIGHT motor direction)
  L298N GND  -> NodeMCU GND (shared ground -- important!)
  L298N 12V  -> Battery pack positive (motor power, NOT from NodeMCU)

  IMPORTANT: NodeMCU logic is 3.3V. Most L298N boards accept 3.3V logic
  on IN1-IN4/ENA/ENB fine, but double check your specific board's
  datasheet if motors don't respond.

  ============ WIRING (motors to L298N) ============
  Left motor  -> L298N OUT1, OUT2
  Right motor -> L298N OUT3, OUT4

  ============ CONNECTION TO RASPBERRY PI 4 ============
  Simplest option: NodeMCU's micro-USB port -> Raspberry Pi 4 USB port.
  This appears on the Pi as /dev/ttyUSB0 (check with `ls /dev/tty*`).
  Make sure hardware_bridge.py's port matches this exactly.

  Baud rate must match hardware_bridge.py's baudrate=115200

  ============ TESTING WITHOUT THE PI ============
  Before connecting to the Pi at all, upload this sketch, open the
  Arduino IDE's Serial Monitor (115200 baud, "Newline" line ending),
  and type commands directly to confirm the wiring works:
      M,50,50   -> both motors should spin forward
      M,0,0     -> both motors should stop
      M,-50,-50 -> both motors should spin backward
*/

// Left motor pins (NodeMCU labeled pins)
const int ENA = D1;
const int IN1 = D2;
const int IN2 = D3;

// Right motor pins
const int ENB = D5;
const int IN3 = D6;
const int IN4 = D7;

void setup() {
  Serial.begin(115200);

  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // ESP8266 defaults to 10-bit PWM (0-1023). We set it to match our
  // 0-255 math below, so the rest of the code stays simple.
  analogWriteRange(255);

  stopMotors();
  Serial.println("Motor controller ready (NodeMCU). Waiting for commands...");
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    parseAndExecute(line);
  }
}

void parseAndExecute(String line) {
  // Expected format: M,<left_pwm>,<right_pwm>
  if (line.length() == 0 || line.charAt(0) != 'M') {
    return;  // ignore anything that doesn't match our protocol
  }

  int firstComma = line.indexOf(',');
  int secondComma = line.indexOf(',', firstComma + 1);

  if (firstComma == -1 || secondComma == -1) {
    return;  // malformed, ignore
  }

  int leftPwm = line.substring(firstComma + 1, secondComma).toInt();
  int rightPwm = line.substring(secondComma + 1).toInt();

  // Clamp to safe range
  leftPwm = constrain(leftPwm, -100, 100);
  rightPwm = constrain(rightPwm, -100, 100);

  setMotor(leftPwm, ENA, IN1, IN2);
  setMotor(rightPwm, ENB, IN3, IN4);
}

void setMotor(int pwmPercent, int enablePin, int in1Pin, int in2Pin) {
  // Convert -100..100 percent to 0..255 PWM value + direction
  int pwmValue = map(abs(pwmPercent), 0, 100, 0, 255);

  if (pwmPercent > 0) {
    // Forward
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
  } else if (pwmPercent < 0) {
    // Backward
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
  } else {
    // Stop
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
  }

  analogWrite(enablePin, pwmValue);
}

void stopMotors() {
  setMotor(0, ENA, IN1, IN2);
  setMotor(0, ENB, IN3, IN4);
}
