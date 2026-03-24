from machine import ADC
import utime
import array
import gc

adc = ADC(26)

TOTAL_SAMPLES = 25000
WINDOW_SIZE = 600
PEAK_OFFSET = 150

# Pre-alocare globala pentru a evita fragmentarea memoriei
audio_buffer = array.array("h", [0] * TOTAL_SAMPLES)

def get_baseline_offset():
    print("Calibrare zgomot fond... (pastreaza linistea 1 sec)")
    suma = 0
    for _ in range(500):
        suma += (adc.read_u16() >> 4)
        utime.sleep_us(200)
    offset = suma // 500
    print("Offset calibrat la:", offset)
    return offset

def capture_and_process_test(offset):
    global audio_buffer 
    
    print("\nPregateste-te (ignor sunetul tastei Enter)...")
    utime.sleep(1)
    
    print("ACUM! Rosteste o vocala scurta...")
    
    for i in range(TOTAL_SAMPLES):
        audio_buffer[i] = (adc.read_u16() >> 4) - offset 
        
    # Filtrul de Pre-accentuare (protejeaza frecventele inalte pentru I si E)
    for i in range(TOTAL_SAMPLES - 1, 0, -1):
        audio_buffer[i] = audio_buffer[i] - int(0.9 * audio_buffer[i-1])
        
    print("Inregistrare captata. Caut potrivirea...")
    
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
        
    print("\n--- INCEPUT DATE PLOTTER ---")
    
    # Filtru de netezire (Moving Average pe 9 puncte) 
    # Rotunjeste varfurile ascutite pentru a parea o sinusoida
    for i in range(len(test_scaled)):
        start_idx = max(0, i - 4)
        end_idx = min(len(test_scaled), i + 5)
        
        suma_locala = 0
        for j in range(start_idx, end_idx):
            suma_locala += test_scaled[j]
            
        valoare_smooth = suma_locala // (end_idx - start_idx)
        print(valoare_smooth)
        
    print("--- SFARSIT DATE PLOTTER ---\n")
        
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
        
    del test_data
    gc.collect()

