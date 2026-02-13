import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import zipfile

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

    # Session State für Abbruch-Funktion
    if "stop_gen" not in st.session_state:
        st.session_state["stop_gen"] = False

    st.title("🎬 Test-Content Sync-Master Studio")

    # --- ZWEI-SPALTEN LAYOUT FÜR DIE HAUPTANZEIGE ---
    main_col_left, main_col_right = st.columns([1, 1.5])

    # --- SIDEBAR: EINSTELLUNGEN ---
    with st.sidebar:
        st.header("⚙️ Konfiguration")
        
        with st.expander("1. Anordnung der Displays", expanded=True):
            cols = st.number_input("Anzahl Displays (Horizontal)", min_value=1, value=4)
            rows = st.number_input("Anzahl Displays (Vertikal)", min_value=1, value=1)
        
        with st.expander("2. Display-Spezifikationen"):
            w_px = st.number_input("Breite pro Display (px)", value=3840)
            h_px = st.number_input("Höhe pro Display (px)", value=2160)
            fps = st.selectbox("Bilder pro Sekunde (FPS)", [30, 60], index=1)

        with st.expander("3. Format & Timing"):
            out_format = st.radio("Ausgabeformat", ["mp4", "png", "jpg"])
            sec_per_display = st.slider("Sekunden pro Display (nur Video)", 2, 20, 10)
        
        with st.expander("4. Personalisierung"):
            custom_text = st.text_input("Zusatz-Text (z.B. Projektname)", "")
            # Hier könnte später ein Logo-Uploader hin
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display if out_format == "mp4" else 0
        
        if out_format == "mp4":
            st.info(f"Gesamtlaufzeit: {total_duration} Sekunden")

    # --- RECHTE SEITE: DYNAMISCHE VORSCHAU ---
    with main_col_right:
        st.subheader("Monitorwand-Vorschau")
        # Simuliere das Setup visuell
        for r in range(rows):
            ui_cols = st.columns(cols)
            for c in range(cols):
                with ui_cols[c]:
                    st.markdown(
                        f"""<div style="border: 3px solid #555; border-radius: 5px; height: 80px; 
                        background-color: #222; display: flex; align-items: center; 
                        justify-content: center; color: #00FF00; font-weight: bold; font-size: 0.8em;">
                        Screen {r+1}x{c+1}</div>""", 
                        unsafe_allow_html=True
                    )
        st.caption(f"Aktuelles Setup: {cols} Spalten x {rows} Zeilen ({total_screens} Displays)")

    # --- LINKE SEITE: AKTIONEN ---
    with main_col_left:
        st.subheader("Steuerung")
        
        btn_col, cancel_col = st.columns(2)
        
        with btn_col:
            generate_trigger = st.button("🚀 Jetzt generieren", use_container_width=True)
        
        with cancel_col:
            if st.button("⏹️ Abbrechen", use_container_width=True):
                st.session_state["stop_gen"] = True

    # --- LOGIK: GENERIERUNG ---
    if generate_trigger:
        st.session_state["stop_gen"] = False
        total_w = cols * w_px
        total_h = rows * h_px
        filenames = []
        
        progress_container = st.container()
        with progress_container:
            st.divider()
            prog_bar = st.progress(0)
            status_txt = st.empty()

            if out_format == "mp4":
                # VIDEO GENERIERUNG
                total_frames = int(total_duration * fps)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writers = []
                for r in range(rows):
                    for c in range(cols):
                        fn = f"display_{r+1}x{c+1}.mp4"
                        filenames.append(fn)
                        writers.append(cv2.VideoWriter(fn, fourcc, fps, (w_px, h_px)))

                for f in range(total_frames):
                    if st.session_state["stop_gen"]:
                        st.warning("Vorgang abgebrochen.")
                        break
                    
                    canvas = Image.new('RGB', (total_w, total_h), (20, 20, 20))
                    d = ImageDraw.Draw(canvas)
                    
                    t_global = f / total_frames
                    x_pos = t_global * total_w
                    y_pos = (int(t_global * rows) * h_px) + (h_px // 2)

                    # Zeichne Animation
                    d.line([(x_pos, 0), (x_pos, total_h)], fill=(255, 255, 255), width=20)
                    d.ellipse([x_pos-150, y_pos-150, x_pos+150, y_pos+150], fill=(0, 255, 0))
                    
                    # Text einfügen
                    if custom_text:
                        d.text((total_w//2, total_h - 100), custom_text, fill=(200, 200, 200))

                    img_np = np.array(canvas)
                    for i in range(total_screens):
                        r_idx = i // cols
                        c_idx = i % cols
                        segment = img_np[r_idx*h_px:(r_idx+1)*h_px, c_idx*w_px:(c_idx+1)*w_px]
                        writers[i].write(cv2.cvtColor(segment, cv2.COLOR_RGB2BGR))
                    
                    if f % 15 == 0:
                        prog_bar.progress(f / total_frames)
                        status_txt.text(f"Rendere Frame {f} von {total_frames}...")

                for w in writers: w.release()

            else:
                # BILD GENERIERUNG (PNG/JPG)
                status_txt.text("Erzeuge Testbilder...")
                full_canvas = Image.new('RGB', (total_w, total_h), (30, 30, 30))
                d = ImageDraw.Draw(full_canvas)
                d.line([(0, 0), (total_w, total_h)], fill=(0, 255, 0), width=15)
                d.line([(0, total_h), (total_w, 0)], fill=(255, 0, 255), width=15)
                
                if custom_text:
                    d.text((50, 50), custom_text, fill=(255, 255, 255))

                for i in range(total_screens):
                    r_idx = i // cols
                    c_idx = i % cols
                    segment = full_canvas.crop((c_idx*w_px, r_idx*h_px, (c_idx+1)*w_px, (r_idx+1)*h_px))
                    
                    # Rahmen und Nummerierung
                    sd = ImageDraw.Draw(segment)
                    sd.rectangle([0, 0, w_px-1, h_px-1], outline=(255, 250, 0), width=30)
                    sd.text((w_px//2, h_px//2), f"POS {r_idx+1}x{c_idx+1}", fill=(255,255,255))
                    
                    fn = f"display_{r_idx+1}x{c_idx+1}.{out_format}"
                    segment.save(fn)
                    filenames.append(fn)
                    prog_bar.progress((i+1)/total_screens)

            # --- ZIP & DOWNLOAD ---
            if not st.session_state["stop_gen"]:
                zip_name = "test_content_package.zip"
                with zipfile.ZipFile(zip_name, 'w') as zipf:
                    for f in filenames:
                        zipf.write(f)
                        os.remove(f)
                
                st.success("Erfolgreich generiert!")
                with open(zip_name, "rb") as bfile:
                    st.download_button("📥 ZIP-Paket herunterladen", data=bfile, file_name=zip_name, use_container_width=True)
