import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
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

    # Initialisierung Session States für Steuerung
    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False
    if "stop_requested" not in st.session_state:
        st.session_state["stop_requested"] = False

    st.title("🎬 Test-Content Sync-Master Studio")

    # --- LAYOUT AUFTEILUNG ---
    main_col_left, main_col_right = st.columns([1, 1.2])

    # --- SIDEBAR: KONFIGURATION ---
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
                bg_color = st.color_picker("Farbe wählen", "#141414")
            elif bg_mode == "Eigenes Bild":
                bg_image = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])

        with st.expander("4. Format & Personalisierung"):
            out_format = st.radio("Ausgabeformat", ["mp4", "png", "jpg"])
            sec_per_display = st.slider("Sekunden pro Display", 2, 20, 10)
            custom_text = st.text_input("Zusatz-Text (Personalisierung)", "")
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display if out_format == "mp4" else 0

    # --- RECHTE SEITE: DYNAMISCHE VORSCHAU ---
    with main_col_right:
        st.subheader("Vorschau Monitorwand")
        preview_grid = st.container()
        with preview_grid:
            for r in range(rows):
                ui_cols = st.columns(cols)
                for c in range(cols):
                    with ui_cols[c]:
                        st.markdown(
                            f"""<div style="border: 2px solid #555; border-radius: 4px; height: 70px; 
                            background-color: {bg_color if bg_mode != 'Eigenes Bild' else '#333'}; 
                            display: flex; align-items: center; justify-content: center; 
                            color: #00FF00; font-family: monospace; font-size: 0.7em; font-weight: bold;">
                            ID: {r+1}x{c+1}</div>""", unsafe_allow_html=True
                        )
        st.caption(f"Gesamt-Auflösung: {cols*w_px} x {rows*h_px} Pixel")

    # --- LINKE SEITE: STEUERUNG ---
    with main_col_left:
        st.subheader("Produktion")
        
        if not st.session_state["is_generating"]:
            if st.button("🚀 High-Speed Generierung starten", use_container_width=True, type="primary"):
                st.session_state["is_generating"] = True
                st.session_state["stop_requested"] = False
                st.rerun()
        else:
            if st.button("⏹️ Abbrechen", use_container_width=True):
                st.session_state["stop_requested"] = True
                st.session_state["is_generating"] = False
                st.rerun()

    # --- HIGH-SPEED GENERIERUNGS LOGIK ---
    if st.session_state["is_generating"]:
        filenames = []
        total_w = cols * w_px
        total_h = rows * h_px
        
        status_info = st.empty()
        prog_bar = st.progress(0)

        # 1. TEMPLATES ERSTELLEN (Einmalige Berechnung für Speed)
        status_info.info("Bereite Hintergrund-Templates vor...")
        if bg_mode == "Eigenes Bild" and bg_image is not None:
            full_bg = Image.open(bg_image).convert("RGB").resize((total_w, total_h), Image.Resampling.LANCZOS)
        else:
            h_hex = bg_color.lstrip('#')
            rgb = tuple(int(h_hex[i:i+2], 16) for i in (0, 2, 4))
            full_bg = Image.new('RGB', (total_w, total_h), rgb)

        display_templates = []
        for i in range(total_screens):
            r_idx, c_idx = i // cols, i % cols
            tmpl = full_bg.crop((c_idx * w_px, r_idx * h_px, (c_idx + 1) * w_px, (r_idx + 1) * h_px))
            draw = ImageDraw.Draw(tmpl)
            # Gitter und Text
            draw.rectangle([0, 0, w_px-1, h_px-1], outline=(80, 80, 80), width=10)
            if custom_text:
                draw.text((w_px // 2, h_px - 150), custom_text, fill=(200, 200, 200))
            # Zu OpenCV Format (BGR)
            display_templates.append(cv2.cvtColor(np.array(tmpl), cv2.COLOR_RGB2BGR))

        # 2. PROZESS: VIDEO ODER BILD
        if out_format == "mp4":
            total_frames = int(total_duration * fps)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writers = [cv2.VideoWriter(f"display_{i//cols + 1}x{i%cols + 1}.mp4", fourcc, fps, (w_px, h_px)) for i in range(total_screens)]

            for f in range(total_frames):
                if st.session_state["stop_requested"]: break
                
                t_global = f / (total_frames - 1)
                x_global = t_global * total_w
                current_active_col = int(x_global // w_px)
                current_active_row = int(t_global * rows)

                for i in range(total_screens):
                    r_i, c_i = i // cols, i % cols
                    if r_i == current_active_row and c_i == current_active_col:
                        # Ball auf diesem Screen: Zeichnen
                        frame = display_templates[i].copy()
                        x_loc = int(x_global % w_px)
                        y_loc = h_px // 2
                        cv2.line(frame, (x_loc, 0), (x_loc, h_px), (255, 255, 255), 30)
                        cv2.circle(frame, (x_loc, y_loc), 130, (0, 255, 0), -1)
                        cv2.circle(frame, (x_loc, y_loc), 130, (255, 255, 255), 8)
                        writers[i].write(frame)
                    else:
                        # Ball nicht hier: Template direkt nutzen
                        writers[i].write(display_templates[i])
                
                if f % 20 == 0:
                    prog_bar.progress(f / total_frames)
                    status_info.info(f"Rendere Frame {f} von {total_frames}...")

            for w in writers: w.release()
            filenames = [f"display_{i//cols + 1}x{i%cols + 1}.mp4" for i in range(total_screens)]
        
        else:
            # BILD-AUSGABE
            status_info.info("Erstelle hochauflösende Testbilder...")
            for i in range(total_screens):
                frame = display_templates[i].copy()
                # Diagonale für Alignment
                r_i, c_i = i // cols, i % cols
                cv2.line(frame, (0,0), (w_px, h_px), (0, 255, 0), 15)
                cv2.putText(frame, f"POS {r_i+1}x{c_i+1}", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 5, (255,255,255), 10)
                
                fname = f"display_{r_i+1}x{c_i+1}.{out_format}"
                cv2.imwrite(fname, frame)
                filenames.append(fname)
                prog_bar.progress((i+1)/total_screens)

        # 3. ZIP-ERSTELLUNG
        if not st.session_state["stop_requested"]:
            zip_name = "test_content_package.zip"
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in filenames:
                    zipf.write(f)
                    os.remove(f)
            
            st.session_state["is_generating"] = False
            status_info.success("✅ Generierung abgeschlossen!")
            with open(zip_name, "rb") as bfile:
                st.download_button("📥 ZIP-Paket herunterladen", data=bfile, file_name=zip_name, use_container_width=True)
        else:
            st.error("🛑 Generierung abgebrochen.")
