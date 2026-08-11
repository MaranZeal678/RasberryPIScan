import time

import platform

# Try to import Raspberry Pi GPIO libraries
# When testing on Mac/PC, we mock the servo so we don't crash
GPIO_AVAILABLE = False

if platform.system() == "Darwin":
    print("INFO: Running on macOS. Using mock servo mode for development.")
elif platform.system() == "Linux":
    try:
        from gpiozero import Servo
        from gpiozero.pins.pigpio import PiGPIOFactory
        GPIO_AVAILABLE = True
        print("INFO: Raspberry Pi environment detected. Hardware GPIO enabled.")
    except (ImportError, ModuleNotFoundError):
        print("WARNING: gpiozero or pigpio not detected. Falling back to mock mode.")
else:
    print(f"INFO: Running on {platform.system()}. Using mock mode.")

class PanTiltServoController:
    def __init__(self, pan_pin=17, tilt_pin=18):
        """
        Initialize the servo motors for panning and tilting.
        pan_pin: The GPIO pin connected to the Pan (Left/Right) servo control wire.
        tilt_pin: The GPIO pin connected to the Tilt (Up/Down) servo control wire.
        """
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        
        # Software limit tracking bounds
        self.min_angle = -90
        self.max_angle = 90
        
        # Initial positions in the center
        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0

        if GPIO_AVAILABLE:
            # We highly recommend pigpio because it provides hardware-generated PWM.
            # Jitter-free positioning for the Servo!
            factory = PiGPIOFactory()
            # Standard servo range pulses
            self.pan_servo = Servo(self.pan_pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
            self.tilt_servo = Servo(self.tilt_pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
            self.pan_servo.value = 0.0  # Center starting position
            self.tilt_servo.value = 0.0
        else:
            self.pan_servo = None
            self.tilt_servo = None

    def set_pan_angle(self, angle):
        angle = max(self.min_angle, min(self.max_angle, angle))
        self.current_pan_angle = angle
        if self.pan_servo:
            norm_value = angle / 90.0
            self.pan_servo.value = max(-1.0, min(1.0, norm_value))

    def set_tilt_angle(self, angle):
        angle = max(self.min_angle, min(self.max_angle, angle))
        self.current_tilt_angle = angle
        if self.tilt_servo:
            norm_value = angle / 90.0
            self.tilt_servo.value = max(-1.0, min(1.0, norm_value))

    def track_target(self, target_x_percent, target_y_percent):
        """
        Adjusts servos so the object is perfectly centered in the frame.
        target_x_percent: 0.0 is left edge, 1.0 is right edge, 0.5 is centered.
        target_y_percent: 0.0 is top edge, 1.0 is bottom edge, 0.5 is centered.
        """
        # Error is how far from center we are
        pan_error = target_x_percent - 0.5
        tilt_error = target_y_percent - 0.5
        
        # Proportional tracking step size. We move faster if the object is further to the side!
        tracking_speed_multiplier = 10.0  

        pan_step = pan_error * tracking_speed_multiplier
        tilt_step = tilt_error * tracking_speed_multiplier
        
        # Only adjust if the target moves significantly (Deadband to avoid jitter)
        if abs(pan_error) > 0.10:
            new_pan_angle = self.current_pan_angle - pan_step 
            self.set_pan_angle(new_pan_angle)
            
        if abs(tilt_error) > 0.10:
            # We add here instead of subtract because camera Y-axis is usually inverted from motor
            # If the tilt motor moves exactly opposite to your needs, flip the '+' to '-'
            new_tilt_angle = self.current_tilt_angle + tilt_step 
            self.set_tilt_angle(new_tilt_angle)
            
        if not self.pan_servo:
            # Running on Mac or standard PC, mock the movement out continuously!
            print(f"[Mock Servo Engine] Targeted Angle --> PAN: {self.current_pan_angle:.1f}° | TILT: {self.current_tilt_angle:.1f}°")

    def cleanup(self):
        """Safely detach signals to prevent damage to the Servo motor layout."""
        if self.pan_servo:
            self.pan_servo.detach()
        if self.tilt_servo:
            self.tilt_servo.detach()
