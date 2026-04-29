from machine import ADC
import utime
import array
import gc

# --- HARDWARE SETUP & CONSTANTS ---
adc = ADC(26)

TOTAL_SAMPLES = 25000  
WINDOW_SIZE = 2400     
PEAK_OFFSET = 600      

# Pre-allocate global buffer to prevent memory fragmentation
audio_buffer = array.array("h", [0] * TOTAL_SAMPLES)

def get_baseline_offset():
    """Calculates the DC bias/background noise level."""
    print("Calibrating background noise... (stay quiet for 1 sec)")
    sum_val = 0
    for _ in range(500):
        sum_val += (adc.read_u16() >> 4)
        utime.sleep_us(200)
    
    offset = sum_val // 500
    print(f"Offset calibrated at: {offset}")
    return offset

def capture_audio(offset):
    """Records audio and applies a pre-emphasis filter."""
    global audio_buffer 
    
    print("\nGet ready...")
    utime.sleep(1)
    print("NOW! Speak the vowel CONTINUOUSLY...")
    
    # Overwrite values in the pre-allocated array (saves RAM)
    for i in range(TOTAL_SAMPLES):
        audio_buffer[i] = (adc.read_u16() >> 4) - offset 
        
    # Pre-emphasis filter (boosts high frequencies)
    for i in range(TOTAL_SAMPLES - 1, 0, -1):
        audio_buffer[i] = audio_buffer[i] - int(0.9 * audio_buffer[i-1])
        
    return audio_buffer

def get_aligned_window(signal, search_start, search_end):
    """Finds the peak in a specific range and extracts a window around it."""
    max_val = -32000
    peak_idx = search_start
    
    # Find the peak index
    for i in range(search_start, search_end):
        if signal[i] > max_val:
            max_val = signal[i]
            peak_idx = i
            
    # Define window boundaries
    start = peak_idx - PEAK_OFFSET
    end = start + WINDOW_SIZE
    
    if start < 0: start = 0
    if end > len(signal): end = len(signal)
    
    # SUPER OPTIMIZATION: Use array instead of list to save RAM!
    res = array.array('h', [0] * WINDOW_SIZE)
    
    # Copy the chunk into our pre-allocated array
    chunk_len = end - start
    for i in range(chunk_len):
        if start + i < len(signal):
            res[i] = signal[start + i]
            
    return res

def save_template(final_samples, label):
    """Saves the processed template to a text file."""
    filename = f"/{label.upper()}_vowel.txt"
    try:
        with open(filename, "w") as f:
            for s in final_samples:
                f.write(f"{s}\n")
        print(f"Template saved successfully: {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")

# ==========================================
# MAIN PROGRAM
# ==========================================
offset = get_baseline_offset()

while True:
    v = input("\nEnter vowel (A, E, I, O, U) or X to exit: ").strip().upper()
    if v == "X": 
        print("Exiting program.")
        break
    if v not in "AEIOU": 
        print("Invalid input. Try again.")
        continue
    
    # Capture the raw audio signal
    raw = capture_audio(offset)
    
    # Extract 3 aligned windows using memory-efficient arrays
    w1 = get_aligned_window(raw, 5000, 10000)
    w2 = get_aligned_window(raw, 10000, 15000)
    w3 = get_aligned_window(raw, 15000, 20000)
    
    # 1. AVERAGING (Using pre-allocated array)
    avg_window = array.array('h', [0] * WINDOW_SIZE)
    for i in range(WINDOW_SIZE):
        avg_window[i] = (w1[i] + w2[i] + w3[i]) // 3
        
    # 2. SCALING (Normalize amplitude to 1000)
    max_amp = 1
    for x in avg_window:
        if abs(x) > max_amp: 
            max_amp = abs(x)
            
    final_scaled = array.array('h', [0] * WINDOW_SIZE)
    for i in range(WINDOW_SIZE):
        final_scaled[i] = int((avg_window[i] * 1000) / max_amp)
        
    # Save the final processed label
    save_template(final_scaled, v)
    
    # Free up memory explicitly
    del w1, w2, w3, avg_window, final_scaled
    gc.collect()
