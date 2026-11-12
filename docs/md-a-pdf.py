"""Convierte un Markdown a PDF A4 con PyMuPDF Story + mistune.

Las imágenes (![pie](ruta)) se resuelven respecto de la carpeta del Markdown. Un comentario
<!-- figura: ruta.png | Pie de figura --> inserta en ese punto una página A4 completa para la
imagen: apaisada si la imagen es más ancha que alta, vertical si no. Sirve para diagramas que
dentro del texto quedarían con letra ilegible.

Con --negro (en cualquier posición) todo el texto, las líneas y las tablas salen en negro sobre
blanco, sin colores ni fondos grises: para entregables que el docente pide en negro.
"""

import io
import os
import sys
import re
import pymupdf
import mistune

sys.stdout.reconfigure(encoding="utf-8")

NEGRO = "--negro" in sys.argv
ARGS = [a for a in sys.argv[1:] if a != "--negro"]
SRC = ARGS[0]
OUT = ARGS[1]
TITULO = ARGS[2] if len(ARGS) > 2 else ""
PIE = ARGS[3] if len(ARGS) > 3 else "Diseño de Software · IEI-050 · Universidad Santo Tomás"

md = io.open(SRC, encoding="utf-8").read()

# Quitar el H1 inicial: va en el encabezado de cada página
md = re.sub(r"^#\s+.*\n", "", md, count=1)

# El bloque de datos inicial («**Clave:** valor» en líneas seguidas) se junta en un
# solo párrafo justificado. Se fuerza un salto duro al final de cada línea.
corte = md.find("\n---")
if corte > 0:
    cabecera, resto = md[:corte], md[corte:]
    cabecera = re.sub(r"(\S)\n(?=\*\*)", r"\1  \n", cabecera)
    md = cabecera + resto

CARPETA_MD = os.path.dirname(os.path.abspath(SRC))
MARCADOR = re.compile(r"<!--\s*figura:\s*(.+?)\s*\|\s*(.+?)\s*-->")

# Tramos de texto separados por las páginas de figura: [(markdown, (imagen, pie) | None)]
tramos = []
inicio = 0
for m in MARCADOR.finditer(md):
    tramos.append((md[inicio : m.start()], (m.group(1), m.group(2))))
    inicio = m.end()
tramos.append((md[inicio:], None))

CSS = """
* { font-family: sans-serif; }
body { font-size: 9.5pt; line-height: 1.45; color: #1a1a1a; }

h2 {
  font-size: 14pt; color: #7c2d12; margin-top: 18pt; margin-bottom: 7pt;
  padding-bottom: 3pt; border-bottom: 1px solid #d6b8a8;
}
h3 { font-size: 11.5pt; color: #9a3412; margin-top: 13pt; margin-bottom: 5pt; }
h4 { font-size: 10pt; color: #333333; margin-top: 10pt; margin-bottom: 4pt; }

p  { margin-top: 0pt; margin-bottom: 6pt; text-align: justify; }
ul, ol { margin-top: 3pt; margin-bottom: 7pt; }
li { margin-bottom: 3pt; }

strong { color: #111111; }
em { color: #444444; }

blockquote {
  background-color: #f6f1ec; margin-left: 8pt; margin-right: 4pt;
  margin-top: 5pt; margin-bottom: 8pt; padding: 6pt 9pt;
  border-left: 3px solid #b45309; color: #262626;
}

code { font-family: monospace; font-size: 8.5pt; color: #7c2d12; }
pre  {
  font-family: monospace; font-size: 8pt; background-color: #f4f4f4;
  padding: 5pt; margin-bottom: 8pt; color: #1f2937;
}

table { margin-top: 5pt; margin-bottom: 9pt; width: 100%; }
th {
  background-color: #7c2d12; color: #ffffff; font-size: 8.5pt;
  padding: 4pt; text-align: left;
}
td { font-size: 8.5pt; padding: 4pt; border-bottom: 1px solid #dddddd; }

hr { margin-top: 9pt; margin-bottom: 9pt; color: #cccccc; }
img { width: 100%; }
"""

ACENTO, GRIS_PIE, GRIS_FIGURA = (0.486, 0.176, 0.070), (0.45, 0.45, 0.45), (0.2, 0.2, 0.2)
if NEGRO:
    # Se declara después del CSS base, así que gana en la cascada.
    CSS += """
body, strong, em, h2, h3, h4, blockquote, code, pre, td { color: #000000; }
h2 { border-bottom: 1px solid #000000; }
blockquote { background-color: #ffffff; border-left: 2px solid #000000; }
pre { background-color: #ffffff; border: 1px solid #000000; }
th { background-color: #ffffff; color: #000000; border-bottom: 1px solid #000000; }
td { border-bottom: 1px solid #000000; }
hr { color: #000000; }
"""
    ACENTO = GRIS_PIE = GRIS_FIGURA = (0, 0, 0)

# Fuentes del sistema (conservan « », — y tildes) y la carpeta del Markdown, para sus imágenes
arch = pymupdf.Archive()
arch.add(r"C:\Windows\Fonts")
arch.add(CARPETA_MD)

MEDIA = pymupdf.paper_rect("a4")
APAISADA = pymupdf.Rect(0, 0, MEDIA.height, MEDIA.width)
MARGEN_SUP = 78  # espacio para el encabezado
AREA = pymupdf.Rect(52, MARGEN_SUP, MEDIA.x1 - 45, MEDIA.y1 - 46)

buf = io.BytesIO()
writer = pymupdf.DocumentWriter(buf)
figuras = []  # (páginas ya escritas, imagen, pie)
paginas = 0
for texto, figura in tramos:
    if texto.strip():
        story = pymupdf.Story(
            html=f"<html><body>{mistune.html(texto)}</body></html>", user_css=CSS, archive=arch
        )
        more = 1
        while more:
            dev = writer.begin_page(MEDIA)
            more, _ = story.place(AREA)
            story.draw(dev)
            writer.end_page()
            paginas += 1
    if figura:
        figuras.append((paginas, *figura))
writer.close()

doc = pymupdf.open("pdf", buf.getvalue())
for posicion, imagen, pie in reversed(figuras):
    ruta = os.path.join(CARPETA_MD, imagen)
    pixmap = pymupdf.Pixmap(ruta)
    hoja = APAISADA if pixmap.width > pixmap.height else MEDIA
    page = doc.new_page(pno=posicion, width=hoja.width, height=hoja.height)
    caja = pymupdf.Rect(45, MARGEN_SUP, hoja.x1 - 45, hoja.y1 - 66)
    page.insert_image(caja, filename=ruta, keep_proportion=True)
    page.insert_text(
        pymupdf.Point(45, hoja.y1 - 50), pie, fontsize=9, fontname="helv", color=GRIS_FIGURA
    )

# Encabezado, pie y numeración (cada página según su orientación)
total = doc.page_count
for i, page in enumerate(doc, start=1):
    ancho, alto = page.rect.width, page.rect.height
    page.draw_line(
        pymupdf.Point(52, 58),
        pymupdf.Point(ancho - 45, 58),
        color=ACENTO,
        width=1.4,
    )
    page.insert_text(
        pymupdf.Point(52, 50),
        TITULO,
        fontsize=10.5,
        fontname="hebo",
        color=ACENTO,
    )
    page.insert_text(
        pymupdf.Point(52, alto - 28),
        PIE,
        fontsize=7.5,
        fontname="helv",
        color=GRIS_PIE,
    )
    etiqueta = f"{i} / {total}"
    page.insert_text(
        pymupdf.Point(ancho - 45 - pymupdf.get_text_length(etiqueta, "helv", 8.5), alto - 28),
        etiqueta,
        fontsize=8.5,
        fontname="helv",
        color=GRIS_PIE,
    )

doc.subset_fonts()
doc.save(OUT, garbage=4, deflate=True)
print(f"OK -> {OUT} | {total} páginas")
