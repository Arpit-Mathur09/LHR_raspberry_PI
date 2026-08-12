import os
import glob
import time

# Initialize 1-Wire drivers
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Base directory where 1-wire devices appear
base_dir = '/sys/bus/w1/devices/'

def get_sensor_folders():
    """Finds all folders starting with '28-' (DS18B20 family code)"""
    return glob.glob(base_dir + '28*')

def read_temp_raw(device_file):
    """Reads raw lines from the sensor file"""
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        return lines
    except Exception:
        return []

def read_temp(device_folder):
    """Parses raw data to get Celsius temperature"""
    device_file = device_folder + '/w1_slave'
    lines = read_temp_raw(device_file)
    
    # Check if read was successful (Line 0 must end with YES)
    if len(lines) < 2 or lines[0].strip()[-3:] != 'YES':
        return None

    # Find the position of 't='
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c
    return None

# --- MAIN LOOP ---
print("🔍 Scanning for DS18B20 sensors on 1-Wire bus...")
sensor_folders = get_sensor_folders()

print(f"✅ Found {len(sensor_folders)} sensors.")
for folder in sensor_folders:
    print(f" - ID: {os.path.basename(folder)}")

if not sensor_folders:
    print("\n❌ No sensors found! Check:")
    print("1. Did you add 'dtoverlay=w1-gpio,gpiopin=18' to /boot/config.txt?")
    print("2. Is the 4.7k resistor connected between Data and 3.3V?")
    print("3. Did you reboot?")
    exit()

print("\nStarting readings (Press Ctrl+C to stop)...")

try:
    while True:
        print("-" * 40)
        timestamp = time.strftime('%H:%M:%S')
        print(f"Time: {timestamp}")
        
        # Read every detected sensor
        for i, folder in enumerate(sensor_folders):
            temp = read_temp(folder)
            sensor_id = os.path.basename(folder)
            
            if temp is not None:
                print(f"Sensor {i+1} [{sensor_id}]: {temp:.2f} °C")
            else:
                print(f"Sensor {i+1} [{sensor_id}]: Read Error / CRC Fail")
        
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped.")