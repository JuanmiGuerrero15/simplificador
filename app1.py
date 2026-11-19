from pathlib import Path
import re
import pandas as pd
import streamlit as st

# Configuración básica de la página
st.set_page_config(page_title="Letra Pequeña", layout="centered")

# --- 1. Cargar el diccionario -------------------------------------------
ruta = Path(__file__).parent / "candidatos_con_explicacion.csv"
df = pd.read_csv(ruta, encoding="utf-8-sig")
df.columns = df.columns.str.strip()
df = df.dropna(subset=["termino", "explicación sencilla"])

# --- 2. Encabezado con Logo y Título ------------------------------------
# Crea dos columnas: una estrecha para el logo y otra ancha para el título
col_logo, col_titulo = st.columns([8, 10], vertical_alignment="center")

with col_logo:
    # Cambia "logo.png" por el nombre exacto de tu archivo de imagen
    ruta_logo = Path(__file__).parent / "logo.png"
    if ruta_logo.exists():
        st.image(str(ruta_logo), width=1000)

with col_titulo:
    st.title(" ")

# --- 3. Cuadro de texto y Botón grande ----------------------------------
texto = st.text_area("Inserte su texto:", height=250)

# Estilo CSS para hacer el botón más alto y llamativo
st.markdown("""
    <style>
    div.stButton > button {
        height: 3.2em;
        font-size: 1.15rem;
        font-weight: bold;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# type="primary" le da el color destacado del tema y use_container_width lo ensancha al 100%
if st.button("Explicar con palabras sencillas", type="primary", use_container_width=True):

    if texto.strip() == "":
        st.warning("Primero escriba o pegue un texto.")
    else:
        # --- 4. Preparar el texto ---------------------------------------
        texto_limpio = texto.lower()

        for signo in ',.;:()¿?¡!"':
            texto_limpio = texto_limpio.replace(signo, " ")

        palabras_pequeñas = ["de", "del", "la", "el", "los", "las", "en", "y", "a", "para", "por", "con"]
        palabras = [p for p in texto_limpio.split() if p not in palabras_pequeñas]
        texto_limpio = " " + " ".join(palabras) + " "

        # --- 5. Buscar las palabras difíciles ---------------------------
        encontradas = []
        formas_para_resaltar = []

        for _, fila in df.iterrows():
            termino = str(fila["termino"]).strip().lower()
            explicacion = str(fila["explicación sencilla"]).strip()

            formas = [termino, termino + "s", termino + "es"]
            if termino.endswith("ón"):
                formas.append(termino[:-2] + "ones")

            for forma in formas:
                if " " + forma + " " in texto_limpio:
                    encontradas.append((termino, explicacion))
                    formas_para_resaltar.extend(formas)
                    break

        # --- 6. Mostrar resultado con resaltado fosforito ---------------
        if encontradas:
            st.subheader("Texto analizado")

            # Ordenamos de más larga a más corta para evitar subrayados parciales
            formas_unicas = sorted(set(formas_para_resaltar), key=len, reverse=True)
            patron = r"\b(" + "|".join(re.escape(f) for f in formas_unicas) + r")\b"

            # Reemplaza cada coincidencia en el texto original manteniendo sus mayúsculas/minúsculas
            texto_resaltado = re.sub(
                patron,
                r'<mark style="background-color: #fff352; color: #000000; padding: 2px 5px; border-radius: 4px; font-weight: 600;">\1</mark>',
                texto,
                flags=re.IGNORECASE,
            )

            # Mostramos el texto dentro de una caja limpia con saltos de línea respetados
            st.markdown(
                f'<div style="background-color: #f8f9fa; color: #1f2937; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb; line-height: 1.7; white-space: pre-wrap;">{texto_resaltado}</div>',
                unsafe_allow_html=True,
            )

            st.subheader("Palabras que pueden resultar difíciles")
            for termino, explicacion in encontradas:
                st.markdown(
                    f'<p><mark style="background-color: #fff352; color: #000000; padding: 1px 5px; border-radius: 4px;"><b>{termino}</b></mark>: {explicacion}</p>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No he encontrado palabras difíciles en este texto.")
