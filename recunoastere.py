from machine import ADC
import utime
import array
import gc

# --- HARDWARE SETUP & CONSTANTS ---
adc = ADC(26)

TOTAL_SAMPLES = 25000 # 25kHz for 1-second recording
WINDOW_SIZE = 2400    # Size of the extracted window
PEAK_OFFSET = 600     # Start 600 points before the peak

# Global pre-allocation to avoid memory fragmentation
audio_buffer = array.array("h", [0] * TOTAL_SAMPLES)

def get_baseline_offset():
    """Calculates the quiet room background noise."""
    print("Calibrating background noise... (keep quiet for 1 sec)")
    sum_val = 0
    for _ in range(500):
        sum_val += (adc.read_u16() >> 4)
        utime.sleep_us(200)
    offset = sum_val // 500
    print("Offset calibrated at:", offset)
    return offset

def capture_and_process_test(offset):
    """Captures the audio, applies pre-emphasis, and extracts the scaled window."""
    global audio_buffer 
    
    print("\nGet ready (ignoring the Enter key sound)...")
    utime.sleep(1)
    
    print("Speak a short vowel...")
    
    for i in range(TOTAL_SAMPLES):
        audio_buffer[i] = (adc.read_u16() >> 4) - offset 
        
    # Pre-emphasis filter (protects high frequencies for I and E)
    for i in range(TOTAL_SAMPLES - 1, 0, -1):
        audio_buffer[i] = audio_buffer[i] - int(0.9 * audio_buffer[i-1])
        
    print("Recording captured. Finding the match...")
    
    max_val = 0
    peak_idx = PEAK_OFFSET
    for i in range(PEAK_OFFSET, TOTAL_SAMPLES - WINDOW_SIZE):
        if abs(audio_buffer[i]) > max_val:
            max_val = abs(audio_buffer[i])
            peak_idx = i
            
    start_win = peak_idx - PEAK_OFFSET
    end_win = start_win + WINDOW_SIZE
    
    if start_win < 0: start_win = 0
    if end_win > len(audio_buffer): end_win = len(audio_buffer)
    
    window = audio_buffer[start_win:end_win]
    
    max_amp = 1
    for val in window:
        if abs(val) > max_amp:
            max_amp = abs(val)
            
    test_scaled = []
    for val in window:
        scaled_val = int((val * 1000) / max_amp)
        test_scaled.append(scaled_val)
        
    while len(test_scaled) < WINDOW_SIZE:
        test_scaled.append(0)
        
    return test_scaled

def load_template(filename):
    """Loads the saved vowel template from memory."""
    samples = []
    try:
        with open(filename, "r") as f:
            for line in f:
                samples.append(int(line.strip()))
        return samples
    except OSError:
        return None

def dtw_distance(s1, s2):
    """Calculates the Dynamic Time Warping distance between two signals."""
    s1_small = [s1[i] for i in range(0, len(s1), 3)]
    s2_small = [s2[i] for i in range(0, len(s2), 3)]
    
    l1, l2 = len(s1_small), len(s2_small)
    
    if l1 == 0 or l2 == 0:
        return float('inf')
    
    prev_row = [float('inf')] * (l2 + 1)
    prev_row[0] = 0
    
    for i in range(1, l1 + 1):
        curr_row = [float('inf')] * (l2 + 1)
        for j in range(1, l2 + 1):
            cost = abs(s1_small[i-1] - s2_small[j-1])
            curr_row[j] = cost + min(prev_row[j], curr_row[j-1], prev_row[j-1])
        prev_row = curr_row
    
    return prev_row[l2]

# --- MAIN EXECUTION ---
vowels = ["A", "E", "I", "O", "U"]

silence_offset = get_baseline_offset()

while True:
    input("Press ENTER to speak a vowel (or CTRL+C to exit)...")
    
    test_data = capture_and_process_test(silence_offset)
    
    best_match = ""
    min_dist = float('inf') 
    
    for v in vowels:
        filename = f"/{v}_vowel.txt"
        template = load_template(filename)
        
        if template is None:
            print(f"Missing template for {v}! Train it first.")
            continue
            
        dist = dtw_distance(test_data, template)
        print(f"Distance to '{v}' : {dist}")
        
        del template
        gc.collect() 
        
        if dist < min_dist:
            min_dist = dist
            best_match = v
                
    if best_match:
        print("=" * 40)
        print(f"RESULT: Recognized vowel >>> {best_match} <<<")
        print("=" * 40)
        print("\n")
        
    del test_data
    gc.collect()
