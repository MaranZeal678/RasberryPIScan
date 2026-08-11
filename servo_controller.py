import time

try:
    from gpiozero import Servo
    from gpiozero.exc import BadPinFactory
    from gpiozero.pins.pigpio import PiGPIOFactory

    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False


class PanTiltServoController:
    def __init__(
        self,
        pan_pin=17,
        tilt_pin=18,
        min_angle=-85.0,
        max_angle=85.0,
        deadband=0.03,
        tracking_gain=20.0,
        max_step=9.0,
        invert_pan=True,
        invert_tilt=True,
    ):
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.deadband = deadband
        self.tracking_gain = tracking_gain
        self.max_step = max_step
        self.invert_pan = invert_pan
        self.invert_tilt = invert_tilt

        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0
        self.factory = None
        self.pan_servo = None
        self.tilt_servo = None
        self.mock_mode = True
        self._last_mock_log = 0.0

        if not GPIO_AVAILABLE:
            print("[servo] gpiozero/pigpio not available. Running in mock mode.")
            return

        try:
            self.factory = PiGPIOFactory()
            self.pan_servo = Servo(
                self.pan_pin,
                min_pulse_width=0.0005,
                max_pulse_width=0.0025,
                pin_factory=self.factory,
            )
            self.tilt_servo = Servo(
                self.tilt_pin,
                min_pulse_width=0.0005,
                max_pulse_width=0.0025,
                pin_factory=self.factory,
            )
            self.pan_servo.value = 0.0
            self.tilt_servo.value = 0.0
            self.mock_mode = False
            print("[servo] pigpio servo control active.")
        except (BadPinFactory, OSError) as exc:
            print(f"[servo] pigpio unavailable ({exc}). Running in mock mode.")
            self.pan_servo = None
            self.tilt_servo = None

    def _clamp_angle(self, angle):
        return max(self.min_angle, min(self.max_angle, angle))

    def _angle_to_value(self, angle):
        return max(-1.0, min(1.0, angle / 90.0))

    def set_pan_angle(self, angle):
        self.current_pan_angle = self._clamp_angle(angle)
        if self.pan_servo:
            self.pan_servo.value = self._angle_to_value(self.current_pan_angle)

    def set_tilt_angle(self, angle):
        self.current_tilt_angle = self._clamp_angle(angle)
        if self.tilt_servo:
            self.tilt_servo.value = self._angle_to_value(self.current_tilt_angle)

    def _step_from_error(self, error):
        step = error * self.tracking_gain
        return max(-self.max_step, min(self.max_step, step))

    def track_target(self, target_x_percent, target_y_percent):
        pan_error = target_x_percent - 0.5
        tilt_error = target_y_percent - 0.5

        if abs(pan_error) > self.deadband:
            pan_step = self._step_from_error(pan_error)
            if self.invert_pan:
                pan_step *= -1.0
            self.set_pan_angle(self.current_pan_angle - pan_step)

        if abs(tilt_error) > self.deadband:
            tilt_step = self._step_from_error(tilt_error)
            if self.invert_tilt:
                tilt_step *= -1.0
            self.set_tilt_angle(self.current_tilt_angle + tilt_step)

        if self.mock_mode:
            now = time.time()
            if now - self._last_mock_log >= 1.0:
                self._last_mock_log = now
                print(
                    "[servo] mock "
                    f"pan={self.current_pan_angle:.1f} "
                    f"tilt={self.current_tilt_angle:.1f}"
                )

    def cleanup(self):
        if self.pan_servo:
            self.pan_servo.detach()
        if self.tilt_servo:
            self.tilt_servo.detach()
