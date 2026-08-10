# hardware.py
""" 
Pipette manager changed , Now Stm32/Controller will send the pipette model string directly to the Pi, and the Pi will parse it to determine the pipette type and volume. This allows for more flexibility in supporting different pipette models without hardcoding them in the Pi software.
->Stm32 will send "T11 P1=<data> P2=<data>" 
->PI sends T11 on startup to request pipette info from the controller, and the controller responds with the pipette model strings for P1 and P2. The Pi then parses these strings to determine the pipette type and volume.
 
 <Edge Case>
<TO Do> Currently on change of Pipette mounting Stm32 automatically send the command to the pipette info to the pi ,but if stm32 is disconnected or not responding PI will keep on showing the last pipette info, so we need to implement a timeout mechanism to reset the pipette info if no update is received from the controller within a certain time frame. This will ensure that the Pi always has accurate information about the pipettes attached to the system.

"""
import os
import glob
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    class _GPIOStub:
        BCM = 11
        OUT = 0
        IN = 1
        PUD_UP = 2
        HIGH = 1
        LOW = 0

        def setmode(self, *args, **kwargs):
            return None

        def setwarnings(self, *args, **kwargs):
            return None

        def setup(self, *args, **kwargs):
            return None

        def output(self, *args, **kwargs):
            return None

        def input(self, *args, **kwargs):
            return 0

        def PWM(self, *args, **kwargs):
            return _DummyPWM()

        def add_event_detect(self, *args, **kwargs):
            return None

    class _DummyPWM:
        def start(self, *args, **kwargs):
            return None

        def ChangeDutyCycle(self, *args, **kwargs):
            return None

    GPIO = _GPIOStub()

try:
    import smbus2
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

try:
    from rpi_ws281x import PixelStrip, Color
    LIGHTS_AVAILABLE = True
except ImportError:
    LIGHTS_AVAILABLE = False

try:
    import bme280
except ImportError:
    bme280 = None


class BacklightController:
    def __init__(self, base_dir="/home/lhr/Robot_Client"):
        self.base_dir = base_dir
        self.backlight_path = self._find_backlight_path()
        self.max_brightness = self._get_max_brightness()

    def _find_backlight_path(self):
        search_paths = [
            "/sys/class/backlight/rpi_backlight",
            "/sys/class/backlight/*",
        ]
        for p in search_paths:
            for match in glob.glob(p):
                if os.path.exists(os.path.join(match, "brightness")):
                    return match
        return None

    def _get_max_brightness(self):
        if not self.backlight_path:
            return 255
        try:
            with open(os.path.join(self.backlight_path, "max_brightness"), "r") as f:
                return int(f.read().strip())
        except Exception:
            return 255

    def get_brightness(self):
        if not self.backlight_path:
            return 50
        try:
            with open(os.path.join(self.backlight_path, "brightness"), "r") as f:
                val = int(f.read().strip())
            return int((val / self.max_brightness) * 100) if self.max_brightness else 50
        except Exception:
            return 50

    def set_brightness(self, level_pct):
        if not self.backlight_path:
            return
        try:
            level_pct = max(5, min(100, int(level_pct)))
            val = int((level_pct / 100.0) * self.max_brightness)
            with open(os.path.join(self.backlight_path, "brightness"), "w") as f:
                f.write(str(val))
        except PermissionError:
            pass
        except Exception:
            pass


class PWMDevice:
    def __init__(self, pin, freq=2000):
        self.pin = pin
        self.freq = freq
        self.pwm = None
        try:
            GPIO.setup(self.pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.pin, self.freq)
            self.pwm.start(0)
        except: pass 

    def set_duty(self, duty):
        val = max(0.0, min(100.0, float(duty)))
        if self.pwm: self.pwm.ChangeDutyCycle(val)


class FanController:
    def __init__(self, pwm_pin, tacho_pin=None, name="Fan"):
        self.pwm_pin = pwm_pin
        self.tacho_pin = tacho_pin
        self.name = name
        self.duty_cycle = 0
        
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pwm_pin, 100) 
        self.pwm.start(0)

        self.rpm = 0
        self._pulse_count = 0
        self._last_time = time.time()
        
        if self.tacho_pin:
            GPIO.setup(self.tacho_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            try:
                GPIO.add_event_detect(self.tacho_pin, GPIO.FALLING, callback=self._tacho_callback)
            except RuntimeError as e:
                print(f"⚠️ Tacho Init Error ({self.name}): {e}")

    def _tacho_callback(self, channel):
        self._pulse_count += 1

    def set_speed(self, percent):
        self.duty_cycle = max(0, min(100, percent))
        self.pwm.ChangeDutyCycle(self.duty_cycle)

    def get_rpm(self):
        if not self.tacho_pin: return 0
        current_time = time.time()
        dt = current_time - self._last_time
        if dt < 0.5: return self.rpm
        
        raw_rpm = (self._pulse_count / 2) * (60 / max(dt, 0.01))
        self.rpm = int(raw_rpm)
        self._pulse_count = 0
        self._last_time = current_time
        return self.rpm


class PIDController:
    def __init__(self, kp=2.0, ki=0.1, kd=0.5):
        self.kp = kp; self.ki = ki; self.kd = kd
        self.target = 0.0
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()
        
    def update(self, current_temp):
        now = time.time()
        dt = now - self.last_time
        if dt <= 0: return 0
        
        error = self.target - current_temp
        p = self.kp * error
        self.integral += error * dt
        self.integral = max(-50, min(50, self.integral)) 
        i = self.ki * self.integral
        d = self.kd * ((error - self.prev_error) / dt)
        
        self.prev_error = error
        self.last_time = now
        return max(-100, min(100, p + i + d))


class SensorManager:
    def __init__(self):
        self.bus = None
        self.bme_address = 0x76
        try:
            if HARDWARE_AVAILABLE:
                self.bus = smbus2.SMBus(1)
                if bme280:
                    self.bme_calibration = bme280.load_calibration_params(self.bus, self.bme_address)
        except Exception as e:
            print(f"⚠️ Sensor Init Error: {e}")

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(int(f.read()) / 1000.0, 1)
        except: return 0.0

    def get_cpu_usage(self):
        try:
            with open("/proc/loadavg", "r") as f:
                load = float(f.read().split()[0])
            return min(100, round((load / 4.0) * 100, 1))
        except: return 0.0

    def get_bme280(self):
        if not self.bus or not bme280: return {"temp": 0, "hum": 0, "press": 0}
        try:
            data = bme280.sample(self.bus, self.bme_address, self.bme_calibration)
            return {"temp": round(data.temperature, 1), "hum": round(data.humidity, 1), "press": round(data.pressure, 1)}
        except: return {"temp": 0, "hum": 0, "press": 0}

    def get_adt75(self):
        if not self.bus: return 0.0
        try:
            data = self.bus.read_i2c_block_data(0x48, 0, 2)
            val = (data[0] << 8) | data[1]
            val >>= 4
            return val * 0.0625
        except: return 0.0

    def get_all(self):
        bme = self.get_bme280()
        return {
            "cpu_temp": self.get_cpu_temp(), "cpu_load": self.get_cpu_usage(),
            "bme_temp": bme["temp"], "bme_hum": bme["hum"], "bme_press": bme["press"],
            "adt_temp": self.get_adt75()
        }


class LightController:
    def __init__(self, pin=18, num_pixels=20):
        self.active = False
        self.strip = None
        if LIGHTS_AVAILABLE:
            try:
                self.strip = PixelStrip(num_pixels, pin, 800000, 10, False, 180, 0)
                self.strip.begin()
            except Exception as e: print(f"⚠️ Light Init Error: {e}")

    def toggle(self, state):
        self.active = state
        if not self.strip: return
        color = Color(255, 255, 255) if state else Color(0, 0, 0)
        try:
            for i in range(self.strip.numPixels()): self.strip.setPixelColor(i, color)
            self.strip.show()
        except RuntimeError as e: print(f"⚠️ Light Update Error: {e}")


class PipetteManager:
    def __init__(self):
        self.slots = {
            "left": {"name": "Slot 1 (P1)", "model": "none", "id": "--", "found": False, "volume_ul": 0.0},
            "right": {"name": "Slot 2 (P2)", "model": "none", "id": "--", "found": False, "volume_ul": 0.0}
        }

    def update_from_t11(self, p1_model: str, p2_model: str) -> bool:
        changed = False

        def apply_slot(slot_key, raw_model):
            nonlocal changed
            slot = self.slots[slot_key]
            is_attached = (raw_model != "none" and len(raw_model) > 0)
            
            if slot["found"] != is_attached or slot["model"] != raw_model:
                slot["found"] = is_attached
                slot["model"] = raw_model if is_attached else "none"
                
                # --- Dynamic Category Label ---
                raw_lower = raw_model.lower()
                if not is_attached:
                    slot["id"] = "--"
                elif "peristaltic" in raw_lower or "pump" in raw_lower:
                    slot["id"] = "Peristaltic Pump"
                elif any(p in raw_lower for p in ["p20", "p300", "p1000", "opentron"]):
                    slot["id"] = "OT-2 Pipette"
                else:
                    slot["id"] = "Custom Module"
                
                # Volume extraction
                if "p20" in raw_lower: slot["volume_ul"] = 20.0
                elif "p300" in raw_lower: slot["volume_ul"] = 300.0
                elif "p1000" in raw_lower: slot["volume_ul"] = 1000.0
                else: slot["volume_ul"] = 0.0
                
                changed = True

        apply_slot("left", p1_model)
        apply_slot("right", p2_model)
        return changed

    def get_state(self):
        return {k: v.copy() for k, v in self.slots.items()}