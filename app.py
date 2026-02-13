import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import zipfile

# --- PASSWORT-SCHUTZ FUNKTION ---
def check_password():
    """Gibt True zurück, wenn der Benutzer das richtige Passwort eingegeben hat."""
    def password_entered():
        """Prüft, ob das eingegebene Passwort korrekt ist."""
        if st.session_state["password"] == "EV_CC#26go":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Bitte Passwort eingeben", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Bitte Passwort eingeben", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Passwort falsch")
        return False
    else:
        return True

# --- HAUPTPROGRAMM ---
if check_password():
    # 1. Titel der Webseite und Layout
    st.set_page_config(page_title="Test-Content Sync-Master Studio", layout="wide")

    st.title("🎬 Test-Content Sync-Master Studio")
    st.write("Präzise Generierung von Test-Inhalten für Multi-Display-Systeme.")

    # --- SIDEBAR: KONFIGURATION ---
    with st.sidebar:
        # 2. Umbenennung in 'Anordnung der Displays'
        st.header("1. Anordnung der Displays")
        # 3. & 4. Spezifische Bezeichnungen für Horizontal/Vertikal
        cols = st.number_input("Anzahl Displays (Horizontal)", min_value=1, value=4)
        rows = st.number_input("Anzahl Displays (Vertikal)", min_value=1, value=1)
        
        st.header("2. Display-Spezifikationen")
        w_px = st.number_input("Breite pro Display (px)", value=3840)
        h_px = st.number_input("Höhe pro Display (px)", value=2160)
        
        st.header("3. Timing & Format")
        sec_per_display = st.slider("Sekunden Sichtbarkeit pro Display", 2, 20, 10)
        fps = st.selectbox("Bilder pro Sekunde (FPS)", [30, 60], index=1)
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display
        st.info(f"Gesamtlaufzeit: {total_duration} Sekunden")

    # --- ANIMATIONS-LOGIK ---
    def generate_sync_content():
        total_w = cols * w_px
        total_h = rows * h_px
        total_frames = int(total_duration * fps)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        filenames = []
        writers = []
        
        for r in range(rows):
            for c in range(cols):
                fn = f"display_{r+1}x{c+1}.mp4"
                filenames.append(fn)
                writers.append(cv2.VideoWriter(fn, fourcc, fps, (w_px, h_px)))

        progress_bar = st.progress(0)
        status_text = st.empty()

        for f in range(total_frames):
            canvas = Image.new('RGB', (total_w, total_h), (20, 20, 20))
            draw = ImageDraw.Draw(canvas)
            
            t_global = f / total_frames
            x_pos = t_global * total_w
            # Pfad-Logik für mehrzeilige Setups
            current_row = int(t_global * rows)
            y_pos = (current_row * h_px) + (h_px // 2)

            # Test-Animation (Linie und Ball)
            draw.line([(x_pos, 0), (x_pos, total_h)], fill=(255, 255, 255), width=20)
            draw.ellipse([x_pos-150, y_pos-150, x_pos+150, y_pos+150], fill=(0, 255, 0))
            
            # Gitterlinien
            for c in range(cols + 1):
                draw.line([(c*w_px, 0), (c*w_px, total_h)], fill=(60, 60, 60), width=5)
            for r in range(rows + 1):
                draw.line([(0, r*h_px), (total_w, r*h_px)], fill=(60, 60, 60), width=5)

            img_np = np.array(canvas)
            for i in range(total_screens):
                r_idx = i // cols
                c_idx = i % cols
                segment = img_np[r_idx*h_px:(r_idx+1)*h_px, c_idx*w_px:(c_idx+1)*w_px]
                writers[i].write(cv2.cvtColor(segment, cv2.COLOR_RGB2BGR))
            
            if f % 20 == 0:
                prog = f / total_frames
                progress_bar.progress(prog)
                status_text.text(f"Berechne Frame {f} von {total_frames}...")

        for w in writers: w.release()
        return filenames

    # --- INTERAKTION ---
    if st.button("🚀 Test-Content jetzt generieren"):
        with st.spinner("Dateien werden gerendert..."):
            files = generate_sync_content()
            
            zip_name = "test_content_package.zip"
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in files:
                    zipf.write(f)
                    if os.path.exists(f):
                        os.remove(f)
                    
            st.success("Erfolgreich generiert!")
            with open(zip_name, "rb") as bfile:
                st.download_button("📥 ZIP-Paket herunterladen", data=bfile, file_name=zip_name)
