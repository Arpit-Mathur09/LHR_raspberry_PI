import serial
import time

# --- Configuration ---
# /dev/serial0 is the primary hardware UART on Pi 4
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 115200

def initialize_serial():
    try:
        # Initialize the port with a 1-second timeout
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        # Flush buffers to remove any 'login' or system junk data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
        return ser
    except serial.SerialException as e:
        print(f"Error: Could not open serial port: {e}")
        return None

def send_gcode(ser, command):
    if ser and ser.is_open:
        try:
            # Ensure the command ends with a newline for the Pico
            full_command = (command + "\n").encode('utf-8')
            ser.write(full_command)
            print(f"Sent: {command}")

            # Wait a small moment for the Pico to process
            time.sleep(0.1)

            # Read the response (ACK)
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8').strip()
                print(f"Pico Response: {response}")
            else:
                print("Wait: No response received.")
                
        except Exception as e:
            print(f"Communication Error: {e}")

# --- Main Test Loop ---
if __name__ == "__main__":
    my_ser = initialize_serial()
    
    if my_ser:
        try:
            while True:
                send_gcode(my_ser, "G28")
                time.sleep(2)
                send_gcode(my_ser, "X10.5 Y20.3")
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nClosing connection...")
            my_ser.close()