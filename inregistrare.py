from machine import ADC
import utime
import array

adc = ADC(26)

# Configurari sincronizate cu scriptul de testare
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

def capture_audio(offset):
    print("\nPregateste-te (ignor sunetul tastei Enter)...")
    utime.sleep(1)
    
    print("ACUM! Rosteste vocala CONTINUU timp de 1 secunda...")
    
    samples = array.array("h", [0] * TOTAL_SAMPLES)
    for i in range(TOTAL_SAMPLES):
        samples[i] = (adc.read_u16() >> 4) - offset 
        
    print("Inregistrare finalizata.")
    return samples

def extract_and_scale_window(signal, start_idx, end_idx):
    max_val = 0
    local_peak_idx = start_idx
    for i in range(start_idx, end_idx):
        if abs(signal[i]) > max_val:
            max_val = abs(signal[i])
            local_peak_idx = i
            
    start_win = local_peak_idx - PEAK_OFFSET
    end_win = start_win + WINDOW_SIZE
    
    if start_win < 0: start_win = 0
    if end_win > len(signal): end_win = len(signal)
    
    window = signal[start_win:end_win]
    
    max_amp = 1
    for val in window:
        if abs(val) > max_amp:
            max_amp = abs(val)
            
    scaled_window = []
    for val in window:
        scaled_val = int((val * 1000) / max_amp)
        scaled_window.append(scaled_val)
        
    while len(scaled_window) < WINDOW_SIZE:
        scaled_window.append(0)
        
    return scaled_window

def save_samples(samples, label):
    filename = f"/{label.upper()}_vocala.txt"
    with open(filename, "w") as f:
        for s in samples:
            f.write(f"{s}\n")
    print(f"Sablonul a fost salvat in: {filename}\n")


# --- MENIU ANTRENARE ---
liniste_offset = get_baseline_offset()

while True:
    print("\n=== MOD ANTRENARE AVANSAT ===")
    vocala = input("Introdu vocala (A, E, I, O, U) sau X pt iesire: ").strip().upper()
    
    if vocala == "X":
        break
    
    if vocala in ["A", "E", "I", "O", "U"]:
        raw_data = capture_audio(liniste_offset)
        
        # Extragem din 3 zone diferite (ajustate pentru noua lungime a inregistrarii)
        part1 = extract_and_scale_window(raw_data, 200, 700)
        part2 = extract_and_scale_window(raw_data, 700, 1200)
        part3 = extract_and_scale_window(raw_data, 1200, 1800)
        
        # Mediem rezultatele
        averaged_template = array.array("h", [0] * WINDOW_SIZE)
        for i in range(WINDOW_SIZE):
            averaged_template[i] = (part1[i] + part2[i] + part3[i]) // 3
            
        save_samples(averaged_template, vocala)
    else:
        print("Vocala invalida. Incearca din nou.")
