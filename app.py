import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import zipfile

# ... (check_password Funktion bleibt gleich) ...

if check_password():
    st.set_page_config(page_title="Test-Content Sync-Master Studio", layout="wide")

    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False
    if "stop_requested" not in st.session_state:
        st.session_state["stop_requested"] = False

    st.title("🎬 Test-Content Sync-Master Studio")

    # --- SIDEBAR & EINSTELLUNGEN (wie gehabt) ---
    with st.sidebar:
        st.header("⚙️ Konfiguration")
        cols = st.number_input("Anzahl Displays (Horizontal)", min_value=1, value=4)
        rows = st.number_input("Anzahl Displays (Vertikal)", min_value=1, value=1)
        w_px = st.number_input("Breite pro Display (px)", value=3840)
        h_px = st.number_input("Höhe pro Display (px)", value=2160)
        fps = st.selectbox("Bilder pro Sekunde (FPS)", [30, 60], index=1)
        
        bg_mode = st.radio("Hintergrund-Typ", ["Standard (Dunkel)", "Farbe (Hex)", "Eigenes Bild"])
        bg_color = st.color_picker("Hintergrundfarbe", "#141414")
        bg_image = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
        
        out_format = st.radio("Ausgabeformat", ["mp4", "png", "jpg"])
        sec_per_display = st.slider("Sekunden pro Display", 2, 20, 10)
        custom_text = st.text_input("Zusatz-Text (Wasserzeichen)", "")

    # --- OPTIMIERTE GENERIERUNGS-LOGIK ---
    if st.button("🚀 Schnelle Generierung starten") or st.session_state["is_generating"]:
        st.session_state["is_generating"] = True
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display
        total_frames = int(total_duration * fps)
        
        # 1. TEMPLATES VORBEREITEN (Zeitfresser eliminieren)
        status_info = st.info("Bereite Hintergrund-Templates vor...")
        
        # Basis-Hintergrund erstellen
        if bg_mode == "Eigenes Bild" and bg_image is not None:
            full_bg = Image.open(bg_image).convert("RGB").resize((cols * w_px, rows * h_px), Image.Resampling.LANCZOS)
        else:
            h = bg_color.lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            full_bg = Image.new('RGB', (cols * w_px, rows * h_px), rgb)

        # Templates für jedes Display zuschneiden und Text/Gitter einbetten
        display_templates = []
        for i in range(total_screens):
            r, c = i // cols, i % cols
            # Ausschnitt nehmen
            tmpl = full_bg.crop((c * w_px, r * h_px, (c + 1) * w_px, (r + 1) * h_px))
            draw = ImageDraw.Draw(tmpl)
            
            # Gitter & Personalisierung einmalig auf Template zeichnen
            draw.rectangle([0, 0, w_px-1, h_px-1], outline=(60, 60, 60), width=5)
            if custom_text:
                draw.text((w_px // 2, h_px - 100), custom_text, fill=(200, 200, 200))
            
            # Zu NumPy konvertieren (OpenCV Format)
            display_templates.append(cv2.cvtColor(np.array(tmpl), cv2.COLOR_RGB2BGR))

        # 2. VIDEO WRITER STARTEN
        writers = []
        filenames = []
        if out_format == "mp4":
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            for i in range(total_screens):
                fn = f"display_{i//cols + 1}x{i%cols + 1}.mp4"
                filenames.append(fn)
                writers.append(cv2.VideoWriter(fn, fourcc, fps, (w_px, h_px)))

        # 3. SCHNELLE RENDERING-SCHLEIFE
        prog_bar = st.progress(0)
        status_text = st.empty()
        cancel_btn = st.button("⏹️ Abbrechen", key="cancel_gen")

        for f in range(total_frames):
            if cancel_btn or st.session_state["stop_requested"]:
                st.session_state["is_generating"] = False
                break

            # Globaler Fortschritt des Balls
            t_global = f / (total_frames - 1)
            x_global = t_global * (cols * w_px)
            active_col = int(x_global // w_px)
            active_row = int(t_global * rows)
            
            # Nur für jedes Display den Frame schreiben
            for i in range(total_screens):
                r_idx, c_idx = i // cols, i % cols
                
                # Ist der Ball/Linie auf diesem Screen?
                # Wir geben einen Puffer von 200px für den Ballradius
                if c_idx == active_col and r_idx == active_row:
                    # Kopiere nur das Template dieses einen Screens
                    frame = display_templates[i].copy()
                    
                    # Zeichne Ball und Linie (LOKAL auf diesem Screen)
                    x_local = int(x_global % w_px)
                    y_local = h_px // 2
                    
                    # Weißer Strich
                    cv2.line(frame, (x_local, 0), (x_local, h_px), (255, 255, 255), 25)
                    # Grüner Ball
                    cv2.circle(frame, (x_local, y_local), 120, (0, 255, 0), -1)
                    cv2.circle(frame, (x_local, y_local), 120, (255, 255, 255), 5) # Outline
                    
                    writers[i].write(frame)
                else:
                    # Wenn der Ball nicht hier ist: Einfach das fertige Template schreiben
                    writers[i].write(display_templates[i])

            if f % 30 == 0:
                prog_bar.progress(f / total_frames)
                status_text.text(f"🚀 High-Speed Rendering: Frame {f}/{total_frames}")

        # Cleanup
        for w in writers: w.release()
        
        # ZIP & Download (wie gehabt)
        if not st.session_state["stop_requested"]:
            # ... (ZIP Logik) ...
            st.success("High-Speed Generierung fertig!")
            st.session_state["is_generating"] = False
