import RPi.GPIO as GPIO
import time

# --- CONFIGURATION ---
FAN_PIN = 13          # The GPIO pin connected to IRF520N 'SIG' or 'PWM'
PWM_FREQ = 20        # 100Hz is efficient for software PWM and MOSFETs

def main():
    # 1. Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN, GPIO.OUT)

    # 2. Initialize PWM
    # We start at 0% speed (OFF)
    fan = GPIO.PWM(FAN_PIN, PWM_FREQ)
    fan.start(0)

    print(f"✅ Fan Controller Started on GPIO {FAN_PIN}")
    print("---------------------------------------")
    print("Type a number (0-100) to set speed.")
    print("Type 'q' or Press CTRL+C to exit.")
    print("---------------------------------------")

    try:
        while True:
            # 3. Get User Input
            user_input = input("Enter Speed (0-100): ").strip()

            if user_input.lower() == 'q':
                break
            
            # 4. Validate and Set Speed
            try:
                speed = float(user_input)
                
                # Clamp value between 0 and 100
                if speed < 0: speed = 0
                if speed > 100: speed = 100
                
                # Apply to Fan
                fan.ChangeDutyCycle(speed)
                print(f"💨 Speed set to: {speed}%")
                
            except ValueError:
                print("❌ Invalid input! Please enter a number.")

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        # 5. Safe Cleanup
        fan.stop()
        GPIO.cleanup()
        print("🛑 Fan Stopped & GPIO Cleaned.")

if __name__ == "__main__":
    main()