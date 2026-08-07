import serial
import time
import sys

# Update port to match your Pi UART device (e.g., /dev/ttyAMA3, /dev/ttyAMA0, or /dev/ttyS0)
SERIAL_PORT = "/dev/ttyAMA3"
BAUD_RATE = 115200

def calculate_checksum(cmd_str: str) -> int:
    """Computes 8-bit XOR checksum matching gcode_parser."""
    checksum = 0
    for char in cmd_str:
        checksum ^= ord(char)
    return checksum & 0xFF

def run_stress_test():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1.0)
        ser.flushInput()
    except Exception as e:
        print(f"❌ Failed to open serial port {SERIAL_PORT}: {e}")
        sys.exit(1)

    total_packets = 0
    valid_packets = 0
    corrupted_packets = 0
    sequence_gaps = 0
    last_seq = None

    start_time = time.time()
    print("=================================================================")
    print(f"🚀 UART Ribbon Cable Reliability Test Started")
    print(f"Port: {SERIAL_PORT} | Baud: {BAUD_RATE}")
    print("Testing for checksum corruptions & frame drops...")
    print("Press Ctrl+C to stop and view final summary.")
    print("=================================================================\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            total_packets += 1

            # Validate framing syntax
            if '*' in line:
                payload, cs_str = line.rsplit('*', 1)
                
                # Reconstruct unchecksummed payload with trailing space
                payload_with_space = payload + " " if not payload.endswith(" ") else payload

                try:
                    rx_cs = int(cs_str)
                    calc_cs = calculate_checksum(payload_with_space)

                    if rx_cs == calc_cs:
                        valid_packets += 1
                        
                        # Verify Sequence Continuity
                        if payload.startswith("N"):
                            try:
                                seq_num = int(payload.split()[0][1:])
                                if last_seq is not None:
                                    expected_seq = (last_seq % 99999) + 1
                                    if seq_num != expected_seq:
                                        gap = abs(seq_num - expected_seq)
                                        sequence_gaps += gap
                                        print(f"⚠️ Sequence Gap Detected: Expected N{expected_seq}, Got N{seq_num} (Lost {gap} frames)")
                                last_seq = seq_num
                            except ValueError:
                                pass
                    else:
                        corrupted_packets += 1
                        print(f"❌ Checksum Mismatch #{corrupted_packets}: Calculated {calc_cs} != Received {rx_cs} | Raw: {line}")

                except ValueError:
                    corrupted_packets += 1
                    print(f"❌ Malformed Checksum Field: {line}")
            else:
                corrupted_packets += 1
                print(f"❌ Unframed Packet Received (Noise): {line}")

            # Print telemetry report every 200 packets
            if total_packets % 200 == 0:
                elapsed = time.time() - start_time
                pps = total_packets / elapsed if elapsed > 0 else 0
                error_rate = (corrupted_packets / total_packets) * 100
                print(f"[{elapsed:.1f}s] RX Total: {total_packets} | OK: {valid_packets} | ERR: {corrupted_packets} ({error_rate:.3f}%) | Drop Gaps: {sequence_gaps} | Speed: {pps:.1f} pkt/s")

    except KeyboardInterrupt:
        print("\n\n================================================")
        print("📊 FINAL TEST RESULTS SUMMARY")
        print("================================================")
        elapsed = time.time() - start_time
        error_rate = (corrupted_packets / total_packets) * 100 if total_packets > 0 else 0
        pps = total_packets / elapsed if elapsed > 0 else 0

        print(f"Test Duration         : {elapsed:.2f} seconds")
        print(f"Total Packets RX      : {total_packets}")
        print(f"Valid Checksum Packets: {valid_packets}")
        print(f"Corrupted Packets     : {corrupted_packets}")
        print(f"Dropped Packet Gaps   : {sequence_gaps}")
        print(f"Throughput            : {pps:.1f} packets/sec")
        print(f"Packet Error Rate     : {error_rate:.4f}%")
        print("------------------------------------------------")

        if corrupted_packets == 0 and sequence_gaps == 0:
            print("✅ EXCELLENT: 100% Signal Integrity over 4ft Ribbon Cable!")
        elif error_rate < 0.1:
            print("⚠️ ACCEPTABLE: Minor noise detected (< 0.1% error rate).")
        else:
            print("❌ POOR SIGNAL INTEGRITY: High corruption/loss. Check GND lines and cable shielding.")
        print("================================================\n")

        ser.close()

if __name__ == "__main__":
    run_stress_test()