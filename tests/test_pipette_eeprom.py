# from test (we say) slot 2 =0x51 for A0 3.3v slot 1 = 0x50 for A0 to GND
# test_pipette_eeprom.py
import smbus2
import time
import sys

# --- CONFIGURATION ---
I2C_BUS = 1
KNOWN_DEVICES = {
    0x48: "ADT75 (Bed Temp)",
    0x76: "BME280 (Environment)",
    0x77: "BME280 (Alternate)"
}

# Standard EEPROM address is usually 0x50. 
# If your pipette uses a different chip, it will show up in the scan.

def scan_i2c_bus():
    """Scans for all connected I2C devices."""
    print(f"\n🔍 Scanning I2C Bus {I2C_BUS}...")
    bus = smbus2.SMBus(I2C_BUS)
    found_devices = []

    for addr in range(0x03, 0x78):
        try:
            bus.write_quick(addr)
            found_devices.append(addr)
        except OSError:
            pass
    
    bus.close()
    
    if not found_devices:
        print("❌ No devices found on I2C bus!")
        return None

    # Filter and display
    pipette_candidates = []
    print("\n------------------------------------------------")
    print(f"{'Address':<10} | {'Status/Device Name':<25}")
    print("------------------------------------------------")
    
    for addr in found_devices:
        hex_addr = f"0x{addr:02X}"
        if addr in KNOWN_DEVICES:
            print(f"{hex_addr:<10} | Found ({KNOWN_DEVICES[addr]})")
        else:
            # This is likely the pipette
            print(f"{hex_addr:<10} | ✅ NEW DEVICE (Possible Pipette)")
            pipette_candidates.append(addr)
    print("------------------------------------------------\n")
    
    return pipette_candidates

def read_eeprom(addr, num_bytes=128):
    """Reads data from the EEPROM."""
    bus = smbus2.SMBus(I2C_BUS)
    data = []
    
    print(f"📖 Reading {num_bytes} bytes from device at 0x{addr:02X}...")
    
    try:
        # STEP 1: Set the Memory Pointer to 0x0000 (Start of memory)
        # Most EEPROMs require a "Dummy Write" to set the read address.
        
        # Try 2-byte addressing first (Common for AT24C32/64/256 etc.)
        # Sending [0x00, 0x00] sets address to 0
        try:
            bus.write_i2c_block_data(addr, 0x00, [0x00])
        except OSError:
            # If 2-byte fails, try 1-byte addressing (Common for small AT24C02/04/08/16)
            print("   (2-byte addressing failed, trying 1-byte...)")
            bus.write_byte(addr, 0x00)
            
        time.sleep(0.01) # Small delay for chip to settle

        # STEP 2: Read Bytes in chunks
        # We read byte-by-byte or in blocks. Reading sequentially is safer for display.
        for i in range(num_bytes):
            byte = bus.read_byte(addr)
            data.append(byte)
            
    except Exception as e:
        print(f"❌ Error reading EEPROM: {e}")
        bus.close()
        return None

    bus.close()
    return data

def hex_dump(data):
    """Prints data in a readable Hex + ASCII format."""
    print("   Offset   Hex Bytes                                       ASCII")
    print("   " + "-"*75)
    
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        
        # Hex Part
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        
        # ASCII Part (replace unprintable chars with .)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        
        print(f"   {i:04X}     {hex_str:<47} {ascii_str}")
    print("\n")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    candidates = scan_i2c_bus()
    
    if not candidates:
        print("❌ No unknown devices found. Is the pipette connected?")
    elif len(candidates) == 1:
        target = candidates[0]
        print(f"🎯 Target Acquired: 0x{target:02X}")
        eeprom_data = read_eeprom(target)
        if eeprom_data:
            hex_dump(eeprom_data)
    else:
        print("⚠️ Multiple new devices found!")
        for i, addr in enumerate(candidates):
            print(f"   [{i}] 0x{addr:02X}")
        
        selection = input("\nEnter the index number of the device to read: ")
        try:
            target = candidates[int(selection)]
            eeprom_data = read_eeprom(target)
            if eeprom_data:
                hex_dump(eeprom_data)
        except:
            print("Invalid selection.")