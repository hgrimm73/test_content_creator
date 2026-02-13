import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import zipfile

st.set_page_config(page_title="Sync-Master Studio Pro", layout="wide")

st.title("🎬 Sync-Master Studio Pro")
st.write("Intelligente Generierung von Test-Content für Multi-Display-Setups.")

# --- SIDEBAR: KONFIGURATION ---
with st.sidebar:
    st.header("1. Layout")
    cols = st.number_input("Spalten (Horizontal)", min_value=1, value=4)
    rows = st.number_input("Zeilen (Vertikal)", min_value=1, value=1)
    
    st.header("2. Display-Specs")
    w_px = st.number_input("Breite pro Display (px)", value=3840)
    h_px = st.number_input("Höhe pro Display (px)", value=2160)
    
    st.header("3. Timing & Format")
    sec_per_display = st.slider("Sekunden Sichtbarkeit pro Display", 2, 20, 10)
    fps = st.selectbox("Bilder pro Sekunde (FPS)", [30, 60], index=1)
    
    # Automatische Berechnung der Gesamtdauer
    total_screens = cols * rows
    total_duration = total_screens * sec_per_display
    st.info(f"Berechnete Gesamtlänge: {total_duration} Sekunden")

# --- ANIMATIONS-LOGIK ---
def generate_sync_content():
    total_w = cols * w_px
    total_h = rows * h_px
    total_frames = total_duration * fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    filenames = []
    writers = []
    
    # Erstelle Writer für jedes Display
    for r in range(rows):
        for c in range(cols):
            fn = f"display_{r+1}x{c+1}.mp4"
            filenames.append(fn)
            writers.append(cv2.VideoWriter(fn, fourcc, fps, (w_px, h_px)))

    progress_bar = st.progress(0)
    status_text = st.empty()

    for f in range(total_frames):
        # 1. Panorama-Canvas
        canvas = Image.new('RGB', (total_w, total_h), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)
        
        # 2. Berechne, welcher Screen gerade 'dran' ist (0 bis total_screens - 1)
        current_screen_idx = int((f / total_frames) * total_screens)
        
        # Berechne Position innerhalb des aktuellen Screens für sanften Übergang
        # x_global und y_global steuern den Ball über das gesamte Raster
        t_global = f / total_frames
        
        # Einfache horizontale Bewegung über alle Screens
        x_pos = t_global * total_w
        # Bei mehreren Zeilen: Z-Bewegung (vereinfacht)
        y_pos = (int(t_global * rows) * h_px) + (h_px // 2)

        # 3. Zeichne Test-Elemente
        draw.line([(x_pos, 0), (x_pos, total_h)], fill=(255, 255, 255), width=20)
        draw.ellipse([x_pos-150, y_pos-150, x_pos+150, y_pos+150], fill=(0, 255, 0))
        
        # Gitter zur Orientierung
        for c in range(cols + 1):
            draw.line([(c*w_px, 0), (c*w_px, total_h)], fill=(60, 60, 60), width=5)

        # 4. In Segmente schneiden und speichern
        img_np = np.array(canvas)
        for i in range(total_screens):
            r_idx = i // cols
            c_idx = i % cols
            segment = img_np[r_idx*h_px:(r_idx+1)*h_px, c_idx*w_px:(c_idx+1)*w_px]
            writers[i].write(cv2.cvtColor(segment, cv2.COLOR_RGB2BGR))
        
        if f % 20 == 0:
            prog = f / total_frames
            progress_bar.progress(prog)
            status_text.text(f"Generiere Frame {f} von {total_frames}...")

    for w in writers: w.release()
    return filenames

# --- UI INTERAKTION ---
if st.button("🚀 Test-Content generieren"):
    files = generate_sync_content()
    
    zip_name = "sync_test_package.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for f in files:
            zipf.write(f)
            os.remove(f)
            
    st.success("Generierung abgeschlossen!")
    with open(zip_name, "rb") as bfile:
        st.download_button("📥 ZIP herunterladen", data=bfile, file_name=zip_name)