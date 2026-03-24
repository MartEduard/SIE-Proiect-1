from machine import ADC
import utime
import array
import gc

adc = ADC(26)

TOTAL_SAMPLES = 25000  
WINDOW_SIZE = 600     
PEAK_OFFSET = 150     

# ==========================================
# SECRETUL: Alocăm memoria o SINGURĂ dată la pornire!
# Nu se va mai fragmenta niciodată.
# ==========================================
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

def capture_audio(offset):
    global audio_buffer # Folosim variabila globala creata la inceput
    
    print("\nPregatește-te...")
    utime.sleep(1)
    print("ACUM! Rosteste vocala CONTINUU...")
    
    # Doar suprascriem valorile (consum 0 de memorie in plus)
    for i in range(TOTAL_SAMPLES):
        audio_buffer[i] = (adc.read_u16() >> 4) - offset 
        
    # Filtrul de Pre-accentuare (pentru vocalele I si E)
    for i in range(TOTAL_SAMPLES - 1, 0, -1):
        audio_buffer[i] = audio_buffer[i] - int(0.9 * audio_buffer[i-1])
        
    return audio_buffer

def get_aligned_window(signal, search_start, search_end):
    max_val = -32000
    peak_idx = search_start
    for i in range(search_start, search_end):
        if signal[i] > max_val:
            max_val = signal[i]
            peak_idx = i
            
    start = peak_idx - PEAK_OFFSET
    end = start + WINDOW_SIZE
    
    if start < 0: start = 0
    if end > len(signal): end = len(signal)
    
    chunk = signal[start:end]
    res = list(chunk)
    while len(res) < WINDOW_SIZE: res.append(0)
    return res

def save_template(final_samples, label):
    filename = f"/{label.upper()}_vocala.txt"
    with open(filename, "w") as f:
        for s in final_samples:
            f.write(f"{s}\n")
    print(f"Sablon salvat cu succes: {filename}")


# --- PROGRAM PRINCIPAL ---
offset = get_baseline_offset()

while True:
    v = input("\nIntrodu vocala (A,E,I,O,U) sau X: ").strip().upper()
    if v == "X": break
    if v not in "AEIOU": continue
    
    raw = capture_audio(offset)
    
    # 25.000 esantioane
    w1 = get_aligned_window(raw, 5000, 10000)
    w2 = get_aligned_window(raw, 10000, 15000)
    w3 = get_aligned_window(raw, 15000, 20000)
    
    # MEDIEREA CERUTA
    avg_window = []
    for i in range(WINDOW_SIZE):
        avg_val = (w1[i] + w2[i] + w3[i]) // 3
        avg_window.append(avg_val)
        
    # SCALARE (Normalizare la 1000)
    max_amp = 1
    for x in avg_window:
        if abs(x) > max_amp: max_amp = abs(x)
        
    final_scaled = []
    for x in avg_window:
        scaled = int((x * 1000) / max_amp)
        final_scaled.append(scaled)
        
    save_template(final_scaled, v)
    
    # Stergem doar variabilele mici create aici, buffer-ul ramane intact!
    del w1, w2, w3, avg_window, final_scaled
    gc.collect()

