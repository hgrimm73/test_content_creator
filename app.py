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

    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False
    if "stop_requested" not in st.session_state:
        st.session_state["stop_requested"] = False

    st.title("🎬 Test-Content Sync-Master Studio")

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

        with st.expander("3. Animation & Modus"):
            anim_mode = st.radio("Animations-Stil", ["Linearer Durchlauf", "Bouncing Ball (Zick-Zack)"])
            ball_speed = st.radio("Ball-Geschwindigkeit", ["Normal (Halb)", "Doppelt (Schnell)"], index=1)
            out_format = st.radio("Ausgabeformat", ["mp4", "png", "jpg"])
            sec_per_display = st.slider("Sekunden pro Display", 2, 20, 10)

        with st.expander("4. Hintergrund & Design"):
            bg_mode = st.radio("Hintergrund-Typ", ["Standard (Dunkel)", "Farbe (Hex)", "Eigenes Bild"])
            bg_color = st.color_picker("Farbe wählen", "#141414")
            bg_image = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
            custom_text = st.text_input("Zusatz-Text (Wasserzeichen)", "")
        
        total_screens = cols * rows
        total_duration = total_screens * sec_per_display if out_format == "mp4" else 0

    # --- RECHTE SEITE: VORSCHAU & DATEINAME ---
    with main_col_right:
        st.subheader("Vorschau & Dateiname")
        
        # Neues Eingabefeld für den Dateinamen
        user_filename = st.text_input("Gewünschter Dateiname (Pflichtfeld)", 
                                      placeholder="z.B. Projekt_Halle_1", 
                                      help="Dieser Name wird den Dateien vorangestellt (z.B. Name_1x1.mp4)")
        
        if not user_filename:
            st.warning("⚠️ Bitte gib einen Dateinamen ein, um die Generierung zu aktivieren.")

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
                            {r+1}x{c+1}</div>""", unsafe_allow_html=True
                        )
        st.caption(f"Gesamt-Auflösung: {cols*w_px} x {rows*h_px} Pixel")

    # --- LINKE SEITE: STEUERUNG ---
    with main_col_left:
        st.subheader("Produktion")
        
        # Button ist nur aktiv, wenn ein Dateiname eingetragen wurde
        if not st.session_state["is_generating"]:
            gen_disabled = not user_filename
            if st.button("🚀 High-Speed Generierung starten", 
                         use_container_width=True, 
                         type="primary", 
                         disabled=gen_disabled):
                st.session_state["is_generating"] = True
                st.session_state["stop_requested"] = False
                st.rerun()
        else:
            if st.button("⏹️ Abbrechen", use_container_width=True):
                st.session_state["stop_requested"] = True
                st.session_state["is_generating"] = False
                st.rerun()

    # --- GENERIERUNGS LOGIK ---
    if st.session_state["is_generating"]:
        filenames = []
        total_w = cols * w_px
        total_h = rows * h_px
        
        status_info = st.empty()
        prog_bar = st.progress(0)

        # 1. TEMPLATES ERSTELLEN
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
            
            # Rahmen
            draw.rectangle([0, 0, w_px-1, h_px-1], outline=(80, 80, 80), width=10)
            
            # Wasserzeichen: 5x größer und unten rechts
            if custom_text:
                # Dynamische Schriftgröße basierend auf Displayhöhe (ca. 15%)
                font_size = int(h_px * 0.15) 
                try:
                    # Falls eine Standard-Schriftart verfügbar ist, sonst Default
                    font = ImageFont.load_default(size=font_size)
                except:
                    font = None # Fallback auf Standard-Draw ohne Größe
                
                # Text-Anker unten rechts (rb = right bottom)
                draw.text((w_px - 100, h_px - 100), custom_text, fill=(200, 200, 200, 128), 
                          anchor="rb", font=font)
                
            display_templates.append(cv2.cvtColor(np.array(tmpl), cv2.COLOR_RGB2BGR))

        # 2. RENDERING
        if out_format == "mp4":
            total_frames = int(total_duration * fps)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Dateinamen-Logik mit Benutzer-Input
            for i in range(total_screens):
                fn = f"{user_filename}_{i//cols + 1}x{i%cols + 1}.mp4"
                filenames.append(fn)
            
            writers = [cv2.VideoWriter(fn, fourcc, fps, (w_px, h_px)) for fn in filenames]

            # Geschwindigkeit anpassen
            speed_mult = 0.5 if ball_speed == "Normal (Halb)" else 1.0
            ball_x, ball_y = 150, 150
            dx = (total_w / (fps * 2.5)) * speed_mult
            dy = (total_h / (fps * 3.7)) * speed_mult

            for f in range(total_frames):
                if st.session_state["stop_requested"]: break
                
                if anim_mode == "Linearer Durchlauf":
                    t_global = f / (total_frames - 1)
                    x_global = t_global * total_w
                    y_global = (int(t_global * rows) * h_px) + (h_px // 2)
                else: # Bouncing Ball
                    ball_x += dx
                    ball_y += dy
                    if ball_x <= 150 or ball_x >= total_w - 150: dx *= -1
                    if ball_y <= 150 or ball_y >= total_h - 150: dy *= -1
                    x_global, y_global = ball_x, ball_y

                for i in range(total_screens):
                    r_i, c_i = i // cols, i % cols
                    if (c_i * w_px - 250 < x_global < (c_i + 1) * w_px + 250) and \
                       (r_i * h_px - 250 < y_global < (r_i + 1) * h_px + 250):
                        
                        frame = display_templates[i].copy()
                        x_loc = int(x_global - (c_i * w_px))
                        y_loc = int(y_global - (r_i * h_px))
                        
                        # Fadenkreuz & Ball
                        cv2.line(frame, (x_loc, 0), (x_loc, h_px), (255, 255, 255), 25)
                        cv2.line(frame, (0, y_loc), (w_px, y_loc), (255, 255, 255), 25)
                        cv2.circle(frame, (x_loc, y_loc), 140, (0, 255, 0), -1)
                        cv2.circle(frame, (x_loc, y_loc), 140, (255, 255, 255), 10)
                        writers[i].write(frame)
                    else:
                        writers[i].write(display_templates[i])
                
                if f % 30 == 0:
                    prog_bar.progress(f / total_frames)
                    status_info.info(f"🚀 High-Speed-Rendern: {int(f/total_frames*100)}%")

            for w in writers: w.release()
        
        else:
            # BILD-AUSGABE (PNG/JPG)
            status_info.info("Erstelle hochauflösende Testbilder...")
            for i in range(total_screens):
                frame = display_templates[i].copy()
                r_i, c_i = i // cols, i % cols
                cv2.line(frame, (0,0), (w_px, h_px), (0, 255, 0), 20)
                cv2.putText(frame, f"SCREEN {r_i+1}x{c_i+1}", (w_px//4, h_px//2), cv2.FONT_HERSHEY_SIMPLEX, 8, (255,255,255), 15)
                
                fname = f"{user_filename}_{r_i+1}x{c_i+1}.{out_format}"
                cv2.imwrite(fname, frame)
                filenames.append(fname)
            prog_bar.progress(100.0)

        # 3. ZIP-ERSTELLUNG
        if not st.session_state["stop_requested"]:
            zip_name = f"{user_filename}_package.zip"
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in filenames:
                    zipf.write(f)
                    os.remove(f)
            
            st.session_state["is_generating"] = False
            status_info.success("✅ Fertig! Das Paket kann heruntergeladen werden.")
            with open(zip_name, "rb") as bfile:
                st.download_button(f"📥 {user_filename} ZIP herunterladen", data=bfile, file_name=zip_name, use_container_width=True)
