import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import zipfile
import time

# --- PASSWORT-SCHUTZ ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("Sicherheits-Check")
        pw = st.text_input("Bitte Passwort eingeben", type="password")
        if st.button("Anmelden"):
            if pw == "EV_CC#26go":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Passwort falsch.")
        return False
    return True

# --- HAUPTPROGRAMM ---
if check_password():
    st.set_page_config(page_title="Test-Content Sync-Master Studio", layout="wide")

    # Initialisierung Session States
    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False
    if "stop_requested" not in st.session_state:
        st.session_state["stop_requested"] = False

    st.title("🎬 Test-Content Sync-Master Studio")

    main_col_left, main_col_right = st.columns([1, 1.5])

    with st.sidebar:
        st.header("⚙️ Konfiguration")
        
        with st.expander("1. Anordnung der Displays", expanded=True):
            cols = st.number_input("Anzahl Displays (Horizontal)", min_value=1, value=4)
            rows = st.number_input("Anzahl Displays (Vertikal)", min_value=1, value=1)
        
        with st.expander("2. Display-Spezifikationen"):
            w_px = st.number_input("Breite pro Display (px)", value=3840)
            h_px = st.number_input("Höhe pro Display (px)", value=2160)
            fps = st.selectbox("Bilder pro Sekunde (FPS)", [30, 60], index=1)

        with st.expander("3. Hintergrund & Design"):
            bg_mode = st.radio("Hintergrund-Typ", ["Standard (Dunkel)", "Farbe (Hex)", "Eigenes Bild"])
            bg_color = "#141414"
            bg_image = None
            
            if bg_mode == "Farbe (Hex)":
                bg_color = st.color_picker("Hintergrundfarbe wählen", "#141414")
            elif bg_mode == "Eigenes Bild":
                bg_image = st.file_uploader("Bild hochladen (JPG/PNG)", type=["jpg", "png", "jpeg"])

        with st.expander("4. Format & Personalisierung"):
            out_format = st.radio("Ausgabeformat", ["mp4", "png", "jpg"])
            sec_per_display = st.slider("Sekunden pro Display (nur Video)", 2, 20, 10)
            custom_text = st.text_input("Zusatz-Text (Wasserzeichen)", "")
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display if out_format == "mp4" else 0

    # --- RECHTE SEITE: DYNAMISCHE VORSCHAU ---
    with main_col_right:
        st.subheader("Monitorwand-Vorschau")
        preview_container = st.container()
        with preview_container:
            for r in range(rows):
                ui_cols = st.columns(cols)
                for c in range(cols):
                    with ui_cols[c]:
                        st.markdown(
                            f"""<div style="border: 2px solid #555; border-radius: 3px; height: 60px; 
                            background-color: {bg_color if bg_mode != 'Eigenes Bild' else '#333'}; 
                            display: flex; align-items: center; justify-content: center; 
                            color: #00FF00; font-size: 0.7em; font-family: monospace;">
                            {r+1}x{c+1}</div>""", unsafe_allow_html=True
                        )
        st.caption(f"Setup: {cols}x{rows} | Gesamt-Auflösung: {cols*w_px}x{rows*h_px} px")

    # --- STEUERUNG ---
    with main_col_left:
        st.subheader("Steuerung")
        
        # Dynamische Button-Anzeige
        if not st.session_state["is_generating"]:
            if st.button("🚀 Generierung starten", use_container_width=True):
                st.session_state["is_generating"] = True
                st.session_state["stop_requested"] = False
                st.rerun()
        else:
            if st.button("⏹️ Abbrechen", use_container_width=True, type="primary"):
                st.session_state["stop_requested"] = True
                st.session_state["is_generating"] = False
                st.rerun()

    # --- GENERIERUNGS-LOGIK ---
    if st.session_state["is_generating"]:
        total_w = cols * w_px
        total_h = rows * h_px
        filenames = []
        
        # Hintergrund vorbereiten
        def get_base_canvas():
            if bg_mode == "Eigenes Bild" and bg_image is not None:
                img = Image.open(bg_image).convert("RGB")
                return img.resize((total_w, total_h), Image.Resampling.LANCZOS)
            else:
                # Hex zu RGB
                h = bg_color.lstrip('#')
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                return Image.new('RGB', (total_w, total_h), rgb)

        prog_placeholder = st.empty()
        status_txt = st.empty()
        
        base_canvas = get_base_canvas()

        if out_format == "mp4":
            total_frames = int(total_duration * fps)
            # mp4v ist Standard, für bessere Qualität oft libx264 (hier limitiert durch env)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            writers = [cv2.VideoWriter(f"display_{i//cols + 1}x{i%cols + 1}.mp4", fourcc, fps, (w_px, h_px)) for i in range(total_screens)]

            for f in range(total_frames):
                if st.session_state["stop_requested"]:
                    break
                
                canvas = base_canvas.copy()
                d = ImageDraw.Draw(canvas)
                
                # Weiche Bewegung berechnen
                t_global = f / (total_frames - 1)
                x_pos = t_global * total_w
                current_row = int(t_global * rows)
                y_pos = (current_row * h_px) + (h_px // 2)

                # Animationselemente (Linie & Ball)
                d.line([(x_pos, 0), (x_pos, total_h)], fill=(255, 255, 255), width=25)
                d.ellipse([x_pos-120, y_pos-120, x_pos+120, y_pos+120], fill=(0, 255, 0), outline=(255,255,255), width=5)
                
                if custom_text:
                    d.text((total_w//2, total_h - 150), custom_text, fill=(255, 255, 255))

                img_np = np.array(canvas)
                for i in range(total_screens):
                    r_idx, c_idx = i // cols, i % cols
                    segment = img_np[r_idx*h_px:(r_idx+1)*h_px, c_idx*w_px:(c_idx+1)*w_px]
                    writers[i].write(cv2.cvtColor(segment, cv2.COLOR_RGB2BGR))
                
                if f % 10 == 0:
                    prog_placeholder.progress(f / total_frames)
                    status_txt.text(f"Verarbeite Frame {f} von {total_frames}...")

            for w in writers: w.release()
            filenames = [f"display_{i//cols + 1}x{i%cols + 1}.mp4" for i in range(total_screens)]

        else:
            # BILD-GENERIERUNG
            status_txt.text("Erzeuge hochauflösende Testbilder...")
            d = ImageDraw.Draw(base_canvas)
            d.line([(0, 0), (total_w, total_h)], fill=(0, 255, 0), width=20)
            d.line([(0, total_h), (total_w, 0)], fill=(255, 0, 255), width=20)

            for i in range(total_screens):
                r_idx, c_idx = i // cols, i % cols
                segment = base_canvas.crop((c_idx*w_px, r_idx*h_px, (c_idx+1)*w_px, (r_idx+1)*h_px))
                sd = ImageDraw.Draw(segment)
                sd.rectangle([0, 0, w_px-1, h_px-1], outline=(255, 250, 0), width=40)
                if custom_text:
                    sd.text((100, 100), custom_text, fill=(255, 255, 255))
                
                fn = f"display_{r_idx+1}x{c_idx+1}.{out_format}"
                segment.save(fn)
                filenames.append(fn)
                prog_placeholder.progress((i+1)/total_screens)

        # --- FERTIGSTELLUNG ---
        if not st.session_state["stop_requested"]:
            zip_name = "test_content_package.zip"
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in filenames:
                    zipf.write(f)
                    os.remove(f)
            
            st.session_state["is_generating"] = False
            st.success("Erfolgreich generiert!")
            with open(zip_name, "rb") as bfile:
                st.download_button("📥 ZIP-Paket herunterladen", data=bfile, file_name=zip_name, use_container_width=True)
        else:
            st.error("Vorgang wurde abgebrochen.")
            st.session_state["is_generating"] = False
