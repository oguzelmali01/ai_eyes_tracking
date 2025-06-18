import cv2
import mediapipe as mp
import threading
import time
import tkinter as tk
import json
import os

# MediaPipe Face Mesh başlat
mp_face_mesh = mp.solutions.face_mesh
face_mesh     = mp_face_mesh.FaceMesh(refine_landmarks=True)

# Landmark ID tanımları
LEFT_EYE_INNER  = 133
LEFT_EYE_OUTER  = 33
LEFT_EYE_TOP    = 159
LEFT_EYE_BOTTOM = 145
LEFT_IRIS       = 468

RIGHT_EYE_INNER  = 362
RIGHT_EYE_OUTER  = 263
RIGHT_EYE_TOP    = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_IRIS       = 473

# Sorular
sorular = [
    {"soru": "Adana'nın plakası nedir?",
     "secenekler": ["01","05","10","15"],
     "dogru": "01"},
    {"soru": "Python'da listeyi ters çevirmek için hangi yöntem kullanılır?",
     "secenekler": ["reverse()","append()","sort()","pop()"],
     "dogru": "reverse()"},
    {"soru": "Türkiye'nin başkenti neresidir?",
     "secenekler": ["İstanbul","İzmir","Ankara","Bursa"],
     "dogru": "Ankara"}
]
soru_no = 0

# Kamera / süre değişkenleri
odakta_gecen_sure = 0
frame_sayisi      = 0
baslangic_zamani  = 0
kamera_calisiyor  = False

def get_gaze_ratios(lm, w, h):
    # X oranı (0=sol,1=sağ)
    lx0 = lm[LEFT_EYE_OUTER].x * w
    lx1 = lm[LEFT_EYE_INNER].x * w
    lix = lm[LEFT_IRIS].x * w
    left_x = (lix - lx0) / (lx1 - lx0)

    rx0 = lm[RIGHT_EYE_OUTER].x * w
    rx1 = lm[RIGHT_EYE_INNER].x * w
    rix = lm[RIGHT_IRIS].x * w
    right_x = (rix - rx0) / (rx1 - rx0)

    # Y oranı (0=üstte,1=altta)
    lyt = lm[LEFT_EYE_TOP].y * h
    lyb = lm[LEFT_EYE_BOTTOM].y * h
    liy = lm[LEFT_IRIS].y * h
    left_y = (liy - lyt) / (lyb - lyt)

    ryt = lm[RIGHT_EYE_TOP].y * h
    ryb = lm[RIGHT_EYE_BOTTOM].y * h
    riy = lm[RIGHT_IRIS].y * h
    right_y = (riy - ryt) / (ryb - ryt)

    return left_x, right_x, left_y, right_y

def kamera_takip():
    global odakta_gecen_sure, frame_sayisi, kamera_calisiyor, baslangic_zamani
    cap = cv2.VideoCapture(0)
    baslangic_zamani = time.time()
    kamera_calisiyor = True

    while kamera_calisiyor:
        ret, frame = cap.read()
        if not ret:
            continue

        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)
        frame_sayisi += 1
        odakta = False

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark
            lx, rx, ly, ry = get_gaze_ratios(lm, w, h)

            horz_centered = 0.35 < lx < 0.65 and 0.35 < rx < 0.65
            vert_centered = 0.35 < ly < 0.65 and 0.35 < ry < 0.65

            if horz_centered and vert_centered:
                odakta = True
                odakta_gecen_sure += 1

            # İris noktalarını çiz
            for idx in (LEFT_IRIS, RIGHT_IRIS):
                cx = int(lm[idx].x * w)
                cy = int(lm[idx].y * h)
                cv2.circle(frame, (cx, cy), 3, (0,255,0), -1)

        durum = "EKRANA BAKIYOR" if odakta else "EKRANA BAKMIYOR"
        cv2.putText(frame, durum, (20,40), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0,255,255), 2, cv2.LINE_AA)

        cv2.imshow("Kamera Takibi", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

# --- TKINTER Arayüz ---
def soruyu_baslat():
    global odakta_gecen_sure, frame_sayisi
    odakta_gecen_sure = 0
    frame_sayisi      = 0
    secili_cevap.set("")
    guncelle_soru()
    threading.Thread(target=kamera_takip, daemon=True).start()

def guncelle_soru():
    soru = sorular[soru_no]
    soru_label.config(text=soru["soru"])
    for i, sec in enumerate(soru["secenekler"]):
        secenek_butonlari[i].config(text=f"{chr(65+i)}) {sec}", value=sec)

def sonraki_soru():
    global soru_no, kamera_calisiyor
    kamera_calisiyor = False
    time.sleep(1)

    elapsed = time.time() - baslangic_zamani
    odak_orani = odakta_gecen_sure / frame_sayisi if frame_sayisi else 0
    cevap      = secili_cevap.get() or "Cevaplanmadı"
    dogru      = sorular[soru_no]["dogru"]
    dogru_mu   = (cevap == dogru)

    veri = {
        "soru_no": soru_no+1,
        "soru": sorular[soru_no]["soru"],
        "secenekler": sorular[soru_no]["secenekler"],
        "secili_cevap": cevap,
        "dogru_cevap": dogru,
        "dogru_mu": dogru_mu,
        "sure_sn": round(elapsed,2),
        "odakli_frame": odakta_gecen_sure,
        "toplam_frame": frame_sayisi,
        "odak_orani": round(odak_orani,2),
        "okuma_tahmini": "Okumuş" if odak_orani>=0.6 else "Okumamış"
    }
    os.makedirs("loglar", exist_ok=True)
    with open(f"loglar/soru_{soru_no+1}_log.json","w",encoding="utf-8") as f:
        json.dump(veri,f,indent=4,ensure_ascii=False)
    print("✅ Log:", veri)

    soru_no += 1
    if soru_no < len(sorular):
        soruyu_baslat()
    else:
        soru_label.config(text="Sınav Bitti!")
        next_btn.config(state="disabled")

# Pencere
root = tk.Tk()
root.title("Online Sınav Takip")
root.geometry("600x400")

secili_cevap = tk.StringVar()
soru_label    = tk.Label(root, text="", font=("Helvetica",16), wraplength=550)
soru_label.pack(pady=20)

secenek_butonlari = []
for _ in range(4):
    rb = tk.Radiobutton(root, text="", variable=secili_cevap,
                        font=("Arial",13), anchor="w", justify="left")
    rb.pack(fill="x",padx=40)
    secenek_butonlari.append(rb)

next_btn = tk.Button(root, text="Sonraki Soru", command=sonraki_soru, font=("Arial",14))
next_btn.pack(pady=20)

soruyu_baslat()
root.mainloop()
