from machine import ADC
import utime
import array
import gc

adc = ADC(26)

TOTAL_SAMPLES = 2000
WINDOW_SIZE = 600
PEAK_OFFSET = 150

def get_baseline_offset():
    print("Calibrare zgomot fond... (pastreaza linistea 1 sec)")
    suma = 0
    for _ in range(500):
        suma += (adc.read_u16() >> 4)
        utime.sleep_us(200)
    offset = suma // 500
    print("Offset calibrat la valoarea:", offset)
    return offset

def capture_and_process_test(offset):
    print("\nPregatește-te (ignor sunetul tastei Enter)...")
    utime.sleep(1)
    
    print("ACUM! Rosteste o vocala scurta...")
    
    raw_samples = array.array("h", [0] * TOTAL_SAMPLES)
    for i in range(TOTAL_SAMPLES):
        raw_samples[i] = (adc.read_u16() >> 4) - offset 
        
    print("Inregistrare captata. Caut potrivirea...")
    
    max_val = 0
    peak_idx = PEAK_OFFSET
    for i in range(PEAK_OFFSET, TOTAL_SAMPLES - WINDOW_SIZE):
        if abs(raw_samples[i]) > max_val:
            max_val = abs(raw_samples[i])
            peak_idx = i
            
    start_win = peak_idx - PEAK_OFFSET
    end_win = start_win + WINDOW_SIZE
    
    if start_win < 0: start_win = 0
    if end_win > len(raw_samples): end_win = len(raw_samples)
    
    window = raw_samples[start_win:end_win]
    
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
    samples = []
    try:
        with open(filename, "r") as f:
            for line in f:
                samples.append(int(line.strip()))
        return samples
    except OSError:
        return None

def dtw_distance(s1, s2):
    # OPTIMIZARE VITEZA: Luam fiecare al 3-lea esantion
    # Reducem drastic numarul de calcule, pastrand forma generala a undei
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

# --- PROGRAMUL PRINCIPAL ---
vocale = ["A", "E", "I", "O", "U"]

liniste_offset = get_baseline_offset()

while True:
    input("Apasa ENTER pentru a rosti o vocala (sau CTRL+C pentru iesire)...")
    
    test_data = capture_and_process_test(liniste_offset)
    
    best_match = ""
    min_dist = float('inf') 
    
    for v in vocale:
        nume_fisier = f"/{v}_vocala.txt"
        template = load_template(nume_fisier)
        
        if template is None:
            print(f"Lipseste sablonul pentru {v}! Antreneaza-l mai intai.")
            continue
            
        dist = dtw_distance(test_data, template)
        print(f"Distanta fata de '{v}' : {dist}")
        
        del template
        gc.collect() 
        
        if dist < min_dist:
            min_dist = dist
            best_match = v
                
    if best_match:
        print("=" * 40)
        print(f"REZULTAT: Am recunoscut vocala >>> {best_match} <<<")
        print("=" * 40)
        print("\n")
