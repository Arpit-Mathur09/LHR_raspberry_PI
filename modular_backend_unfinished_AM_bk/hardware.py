# hardware.py
import os
import glob
import time
import RPi.GPIO as GPIO

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
    def __init__(self, bus_id=1):
        self.bus_id = bus_id
        self.slots = {
            "left": {"addr": 0x50, "name": "Slot 1", "model": None, "id": None, "found": False},
            "right": {"addr": 0x51, "name": "Slot 2", "model": None, "id": None, "found": False}
        }
        self.scan_pipettes()

    def read_string(self, bus, addr, start_mem, length):
        try:
            bus.write_byte(addr, start_mem)
            chars = []
            for _ in range(length):
                byte = bus.read_byte(addr)
                if byte != 0xFF and 32 <= byte <= 126: chars.append(chr(byte))
            return "".join(chars).strip()
        except: return None

    def scan_pipettes(self):
        changed = False
        if not HARDWARE_AVAILABLE: return False
        try: bus = smbus2.SMBus(self.bus_id)
        except: return False

        for key, slot in self.slots.items():
            addr = slot["addr"]; was_found = slot["found"]
            try:
                bus.write_quick(addr)
                mfg = self.read_string(bus, addr, 0x00, 8)
                if mfg and "opentron" in mfg.lower():
                    if not was_found:
                        slot["found"] = True
                        slot["id"] = self.read_string(bus, addr, 0x30, 20) or "Unknown ID"
                        slot["model"] = self.read_string(bus, addr, 0x60, 20) or "Unknown Model"
                        print(f"✅ Pipette Attached {slot['name']}: {slot['model']}")
                        changed = True
                else:
                    if was_found:
                        slot["found"] = False; slot["id"] = slot["model"] = None; changed = True
            except OSError:
                if was_found:
                    slot["found"] = False; slot["id"] = slot["model"] = None; changed = True
        bus.close()
        return changed

    def get_state(self):
        return {k: v.copy() for k, v in self.slots.items()}