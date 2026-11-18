# app_html.py
# Versión Streamlit del simplificador con expresiones regulares.
# La lógica (pasos 1, 2 y 3) es la misma que en simplificador.py.
# Cambia solo cómo se pide el texto (cuadro + botón) y cómo se muestra
# el resultado (dentro de la propia página, sin abrir otra ventana).
#
# Librerías: csv, re, html, pathlib (vienen con Python) y streamlit.

import csv
import re
import html
from pathlib import Path

import streamlit as st

CARPETA = Path(__file__).parent
CSV = CARPETA / "candidatos_con_explicacion.csv"

# Palabras pequeñas que pueden aparecer en medio de una expresión.
# En el CSV pone "nulidad pleno derecho", pero en el texto real
# pone "nulidad DE pleno derecho".
RELLENO = r"(?:\s+(?:de|del|la|el|los|las|en|y|a|para|por|con)\b)*\s+"


# ---------------------------------------------------------------
# PASO 1: leer el diccionario desde el CSV
# ---------------------------------------------------------------
def patron_de_palabra(palabra):
    """Convierte una palabra en un patrón que acepta plural y género.
    resolución -> resolución / resoluciones
    público    -> público / pública / públicos / públicas
    plazo      -> plazo / plazos  (la "o" final se cambia por o/a, con s opcional)
    """
    palabra = palabra.lower()
    if palabra.endswith("ón"):
        return re.escape(palabra[:-2]) + "(?:ón|ones)"
    if palabra.endswith("o"):
        return re.escape(palabra[:-1]) + "[oa]s?"
    return re.escape(palabra) + "(?:s|es)?"


def cargar_diccionario():
    """Devuelve una lista de entradas. Cada entrada tiene:
    termino, explicacion y patron (la expresión que lo busca en el texto)."""
    entradas = []
    with open(CSV, encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f):
            termino = fila["termino"].strip()
            explicacion = fila["explicación sencilla"].strip()
            if not termino or not explicacion:   # sin explicación = no entra
                continue
            partes = [patron_de_palabra(p) for p in termino.split()]
            patron = r"\b" + RELLENO.join(partes) + r"\b"
            entradas.append({
                "termino": termino,
                "explicacion": explicacion,
                "patron": re.compile(patron, re.IGNORECASE),
            })
    # Los términos largos primero, para que "dominio público"
    # se marque antes que "público" suelto.
    entradas.sort(key=lambda e: len(e["termino"]), reverse=True)
    return entradas


# ---------------------------------------------------------------
# PASO 2: encontrar las palabras difíciles en el texto
# ---------------------------------------------------------------
def detectar(texto, entradas):
    """Devuelve una lista de (inicio, fin, entrada), ordenada por posición."""
    ocupado = []      # trozos del texto que ya están marcados
    hallazgos = []
    for entrada in entradas:
        for m in entrada["patron"].finditer(texto):
            # si este trozo se solapa con uno ya marcado, lo saltamos
            if any(m.start() < fin and m.end() > ini for ini, fin in ocupado):
                continue
            ocupado.append((m.start(), m.end()))
            hallazgos.append((m.start(), m.end(), entrada))
    hallazgos.sort(key=lambda h: h[0])
    return hallazgos


# ---------------------------------------------------------------
# PASO 3: construir el HTML
# ---------------------------------------------------------------
def marcar_texto(texto, hallazgos):
    """Devuelve el texto en HTML, con cada palabra difícil dentro de un <span>."""
    trozos = []
    posicion = 0
    for ini, fin, entrada in hallazgos:
        trozos.append(html.escape(texto[posicion:ini]))        # texto normal
        explicacion = html.escape(entrada["explicacion"], quote=True)
        palabra = html.escape(texto[ini:fin])
        trozos.append(
            f'<span class="dificil" tabindex="0" data-explicacion="{explicacion}">'
            f'{palabra}</span>'
        )
        posicion = fin
    trozos.append(html.escape(texto[posicion:]))               # resto del texto
    return "".join(trozos).replace("\n", "<br>")


PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: Arial, sans-serif; font-size: 24px; line-height: 1.8;
         margin: 0; padding: 10px 12px 160px 12px; color: #111; background: #fff; }
  .aviso { background: #eef3f8; padding: 12px 16px; border-radius: 8px; font-size: 20px; }
  .dificil { background: #fff3a8; border-bottom: 3px solid #e0a800;
             padding: 0 3px; cursor: help; position: relative; outline: none; }
  .dificil:hover::after, .dificil:focus::after {
      content: attr(data-explicacion);
      position: absolute; left: 0; top: 100%; z-index: 10;
      width: 300px; max-width: 80vw; background: #1b3a57; color: white;
      padding: 12px 14px; border-radius: 8px; font-size: 20px; line-height: 1.4; }
  /* Si la palabra está cerca del borde derecho, la explicación se alinea a la derecha */
  .dificil.derecha:hover::after, .dificil.derecha:focus::after { left: auto; right: 0; }
</style>
</head>
<body>
<p class="aviso">Las palabras <span class="dificil">marcadas en amarillo</span>
tienen explicación: pase el cursor por encima o tóquelas.</p>
<p>%TEXTO%</p>
<script>
  // Al pasar el cursor o tocar una palabra, comprobamos si la explicación
  // (300 px de ancho) cabe hacia la derecha. Si no cabe, se alinea a la derecha.
  document.querySelectorAll(".dificil").forEach(function (el) {
    function colocar() {
      var espacio = window.innerWidth - el.getBoundingClientRect().left;
      el.classList.toggle("derecha", espacio < 330);
    }
    el.addEventListener("mouseenter", colocar);
    el.addEventListener("focus", colocar);
  });
</script>
</body>
</html>
"""


def generar_pagina(texto, entradas):
    """Devuelve la página HTML completa y cuántas palabras se han marcado."""
    hallazgos = detectar(texto, entradas)
    pagina = PLANTILLA.replace("%TEXTO%", marcar_texto(texto, hallazgos))
    return pagina, len(hallazgos)


# ---------------------------------------------------------------
# INTERFAZ (Streamlit)
# ---------------------------------------------------------------
st.title("📄 Entiende tus papeles")

# Sustituye al input(): un cuadro grande donde pegar el texto
texto = st.text_area("Pegue aquí el texto que no entiende:", height=250)

# Sustituye a "ejecutar el programa": solo se hace algo al pulsar el botón
if st.button("Explicar con palabras sencillas"):

    if texto.strip() == "":
        st.warning("Primero escriba o pegue un texto.")
    else:
        entradas = cargar_diccionario()
        pagina, n = generar_pagina(texto, entradas)

        if n == 0:
            st.info("No he encontrado palabras difíciles en este texto.")
        else:
            st.success(f"He encontrado {n} palabras o expresiones que pueden resultar difíciles.")

        # Sustituye a webbrowser.open(): muestra la página dentro de la app.
        # height="content" hace que se ajuste sola a la altura del texto.
        st.iframe(pagina, height="content")
