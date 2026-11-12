"""Genera los cuatro diagramas UML de la agenda de citas, en negro sobre blanco.

Fuente de verdad: docs/caso-agenda.md (secciones 4 a 8). Los nombres de participantes, los
mensajes, las guardas, la numeración y las firmas de las clases coinciden con ese contrato
carácter por carácter, y con el código de `agenda_citas/`.

Salidas en docs/diagramas/ (trazo de 3 px, todo en escala de grises):
  1-actividades.png     diagrama de actividades con tres carriles (Paciente, PantallaAgenda, Agenda)
  2-secuencia.png       diagrama de secuencia, escenario A (alt [disponible] / [else])
  3-comunicacion.png    diagrama de comunicación con numeración decimal anidada
  4-clases.png          diagrama de clases con visibilidad, tipos, firmas y multiplicidades

`Lienzo` dibuja a doble resolución y reduce al guardar, para suavizar diagonales y curvas.
Arial no trae los glifos de rombo ni de triángulo hueco: esas figuras se dibujan como polígonos.
Uso: .venv/Scripts/python docs/generar_diagramas.py

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent
SALIDA = AQUI / "diagramas"
FUENTES = "C:/Windows/Fonts/"
TRAZO = 3
S = 2  # factor de supersampling


class Lienzo:
    """Lienzo con coordenadas lógicas; internamente dibuja a escala S."""

    def __init__(self, w, h, tam=26):
        self.w, self.h, self.tam = w, h, tam
        self.img = Image.new("RGB", (w * S, h * S), "white")
        self.d = ImageDraw.Draw(self.img)
        arch = {"n": "arial", "b": "arialbd", "i": "ariali", "bi": "arialbi"}
        self.f = {e: ImageFont.truetype(f"{FUENTES}{a}.ttf", tam * S) for e, a in arch.items()}

    @staticmethod
    def _p(pt):
        return (pt[0] * S, pt[1] * S)

    def ancho(self, t, e="n"):
        return self.f[e].getlength(t) / S

    # ---- trazos -------------------------------------------------------------------------
    def linea(self, pts, punteada=False):
        if not punteada:
            self.d.line([self._p(p) for p in pts], fill=0, width=TRAZO * S, joint="curve")
            return
        for a, b in zip(pts, pts[1:], strict=False):
            largo = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uy = (b[0] - a[0]) / largo, (b[1] - a[1]) / largo
            t = 0
            while t < largo:
                t2 = min(t + 14, largo)
                self.d.line(
                    [
                        self._p((a[0] + ux * t, a[1] + uy * t)),
                        self._p((a[0] + ux * t2, a[1] + uy * t2)),
                    ],
                    fill=0,
                    width=TRAZO * S,
                )
                t += 24

    def punta(self, desde, hasta, tipo, largo=24, abre=0.42):
        ang = math.atan2(hasta[1] - desde[1], hasta[0] - desde[0])
        p1 = (hasta[0] - largo * math.cos(ang - abre), hasta[1] - largo * math.sin(ang - abre))
        p2 = (hasta[0] - largo * math.cos(ang + abre), hasta[1] - largo * math.sin(ang + abre))
        if tipo == "llena":
            self.d.polygon([self._p(hasta), self._p(p1), self._p(p2)], fill=0)
        else:
            self.d.line(
                [self._p(p1), self._p(hasta), self._p(p2)], fill=0, width=TRAZO * S, joint="curve"
            )

    def flecha(self, pts, tipo="abierta", punteada=False):
        """Polilínea con punta en el último punto."""
        pts = list(pts)
        previo, punta = pts[-2], pts[-1]
        if tipo == "llena":  # acorta la línea para que no asome por la punta
            ang = math.atan2(punta[1] - previo[1], punta[0] - previo[0])
            pts[-1] = (punta[0] - 18 * math.cos(ang), punta[1] - 18 * math.sin(ang))
        self.linea(pts, punteada)
        self.punta(previo, punta, tipo)

    def rect(self, x0, y0, x1, y1, relleno="white", r=0):
        caja = [x0 * S, y0 * S, x1 * S, y1 * S]
        if r:
            self.d.rounded_rectangle(caja, radius=r * S, outline=0, fill=relleno, width=TRAZO * S)
        else:
            self.d.rectangle(caja, outline=0, fill=relleno, width=TRAZO * S)

    def circulo(self, cx, cy, r, relleno=None):
        self.d.ellipse(
            [(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
            outline=0,
            fill=relleno if relleno is not None else "white",
            width=TRAZO * S,
        )

    def poligono(self, pts, relleno="white"):
        self.d.polygon([self._p(p) for p in pts], fill=relleno)
        self.d.line([self._p(p) for p in [*pts, pts[0]]], fill=0, width=TRAZO * S, joint="curve")

    # ---- texto --------------------------------------------------------------------------
    def texto(self, x, y, s, e="n", anc="mm", fondo=False, subrayado=False):
        """Texto en (x, y). anc: 'mm' centrado, 'lm' izquierda, 'rm' derecha."""
        fuente = self.f[e]
        if fondo:
            bx = self.d.textbbox((x * S, y * S), s, font=fuente, anchor=anc)
            self.d.rectangle(
                [bx[0] - 6 * S, bx[1] - 2 * S, bx[2] + 6 * S, bx[3] + 2 * S], fill="white"
            )
        self.d.text((x * S, y * S), s, font=fuente, fill=0, anchor=anc)
        if subrayado:
            asc, desc = fuente.getmetrics()
            base = y * S + (asc - desc) / 2
            w = fuente.getlength(s)
            izq = x * S - w / 2 if anc == "mm" else x * S
            self.d.line([izq, base + 6 * S, izq + w, base + 6 * S], fill=0, width=2 * S)

    def parrafo(self, x, y, s, e="n", paso=34):
        lineas = s.split("\n")
        y0 = y - (len(lineas) - 1) * paso / 2
        for k, linea in enumerate(lineas):
            self.texto(x, y0 + k * paso, linea, e)

    # ---- figuras UML ----------------------------------------------------------------------
    def monigote(self, x, cy, nombre="Paciente"):
        """Actor: monigote centrado en cy (cuerpo), nombre debajo."""
        self.circulo(x, cy - 65, 20)
        self.linea([(x, cy - 45), (x, cy + 20)])
        self.linea([(x - 36, cy - 28), (x + 36, cy - 28)])
        self.linea([(x - 30, cy + 76), (x, cy + 20), (x + 30, cy + 76)])
        self.texto(x, cy + 108, nombre)

    def caja_objeto(self, cx, cy, nombre, alto=70):
        w = self.ancho(nombre) + 44
        self.rect(cx - w / 2, cy - alto / 2, cx + w / 2, cy + alto / 2)
        self.texto(cx, cy, nombre, subrayado=True)
        return cx - w / 2, cy - alto / 2, cx + w / 2, cy + alto / 2

    def guardar(self, nombre):
        SALIDA.mkdir(exist_ok=True)
        ruta = SALIDA / nombre
        self.img.resize((self.w, self.h), Image.LANCZOS).convert("L").save(ruta, optimize=True)
        return ruta


# =======================================================================================
# 1 · Diagrama de actividades (sección 6 del contrato)
# =======================================================================================
def actividades():
    W, H = 2500, 1760
    L = Lienzo(W, H)
    x0, lw, top, enc = 50, 800, 40, 80
    bot = H - 40
    cu, cp, cr = (x0 + lw * i + lw // 2 for i in range(3))  # centros de los carriles
    L.rect(x0, top, x0 + 3 * lw, bot)
    for i in (1, 2):
        L.linea([(x0 + lw * i, top), (x0 + lw * i, bot)])
    L.linea([(x0, top + enc), (x0 + 3 * lw, top + enc)])
    for c, n in ((cu, "Paciente"), (cp, "PantallaAgenda"), (cr, "Agenda")):
        L.texto(c, top + enc / 2, n, "b")

    def accion(cx, cy, txt):
        lineas = txt.split("\n")
        w = max(L.ancho(ln) for ln in lineas) + 70
        h = 36 * len(lineas) + 44
        L.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=26)
        L.parrafo(cx, cy, txt, paso=36)
        return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2

    # nodo inicial
    L.circulo(cu, 200, 24, relleno=0)
    a1 = accion(cu, 340, "Ingresar profesional,\nfecha y hora")
    L.flecha([(cu, 224), (cu, a1[1])])

    a2 = accion(cp, 510, "Enviar la solicitud")
    L.flecha([(cu, a1[3]), (cu, 510), (a2[0], 510)])

    a3 = accion(cr, 680, "Verificar el bloque\n(franja + cita activa)")
    L.flecha([(cp, a2[3]), (cp, 680), (a3[0], 680)])

    # decisión
    dy, mw, mh = 890, 190, 85
    L.poligono([(cr, dy - mh), (cr + mw, dy), (cr, dy + mh), (cr - mw, dy)])
    L.flecha([(cr, a3[3]), (cr, dy - mh)])

    # camino [bloque ocupado o fuera de franja]
    sup = accion(cp, 1100, "Mostrar\n«Bloque no disponible»")
    L.flecha([(cr - mw, dy), (cp, dy), (cp, sup[1])])
    L.texto((cr - mw + cp) / 2, dy - 28, "[bloque ocupado o fuera de franja]", fondo=True)
    fy = 1260
    L.circulo(cp, fy, 30)
    L.circulo(cp, fy, 17, relleno=0)
    L.flecha([(cp, sup[3]), (cp, fy - 30)])

    # camino [bloque disponible]
    cre = accion(cr, 1140, "Crear la cita")
    L.flecha([(cr, dy + mh), (cr, cre[1])])
    L.texto(cr + 18, dy + mh + 38, "[bloque disponible]", anc="lm")
    agr = accion(cr, 1310, "Registrar la cita")
    L.flecha([(cr, cre[3]), (cr, agr[1])])
    reg = accion(cp, 1510, "Mostrar\n«Cita registrada»")
    L.flecha([(cr, agr[3]), (cr, 1510), (reg[2], 1510)])
    fy2 = 1660
    L.circulo(cp, fy2, 30)
    L.circulo(cp, fy2, 17, relleno=0)
    L.flecha([(cp, reg[3]), (cp, fy2 - 30)])
    return L.guardar("1-actividades.png")


# =======================================================================================
# 2 · Diagrama de secuencia (sección 7 del contrato)
# =======================================================================================
def secuencia():
    W, H = 4050, 1900
    L = Lienzo(W, H)
    X = {"U": 170, "P": 880, "A": 1700, "R": 2450, "Pr": 3150, "C": 3800}
    BARRA = 11  # semiancho de las barras de activación
    FIN = H - 50

    # cabeceras
    yc = 75
    L.monigote(X["U"], 120)
    cab = {
        "P": L.caja_objeto(X["P"], yc, ":PantallaAgenda"),
        "A": L.caja_objeto(X["A"], yc, "agenda:Agenda"),
        "R": L.caja_objeto(X["R"], yc, ":RepositorioAgenda"),
        "Pr": L.caja_objeto(X["Pr"], yc, "rojas:Profesional"),
    }
    y_create = 1010
    cab["C"] = L.caja_objeto(X["C"], y_create, "c:Cita")

    # líneas de vida (c:Cita nace con el «create» y sigue viva: llega abajo como las demás)
    L.linea([(X["U"], 240), (X["U"], FIN)], punteada=True)
    for k in ("P", "A", "R", "Pr", "C"):
        L.linea([(X[k], cab[k][3]), (X[k], FIN)], punteada=True)

    # fragmento alt (marco primero; barras y mensajes encima)
    y_sep = 1520
    ax0, ay0, ax1, ay1 = X["P"] - 300, 870, X["C"] + 160, 1830
    L.rect(ax0, ay0, ax1, ay1, relleno=None)
    L.poligono(
        [(ax0, ay0), (ax0 + 100, ay0), (ax0 + 100, ay0 + 22), (ax0 + 84, ay0 + 42), (ax0, ay0 + 42)]
    )
    L.texto(ax0 + 44, ay0 + 21, "alt")
    L.linea([(ax0, y_sep), (ax1, y_sep)], punteada=True)
    L.texto(ax0 + 22, ay0 + 75, "[disponible]", anc="lm")
    L.texto(ax0 + 22, y_sep + 35, "[else]", anc="lm")

    def barra(k, y0, y1, desp=0):
        L.rect(X[k] - BARRA + desp, y0, X[k] + BARRA + desp, y1)

    barra("P", 300, 1800)
    barra("A", 410, 1700)
    barra("R", 520, 600)
    barra("R", 1210, 1270)
    barra("Pr", 710, 790)
    barra("Pr", 1110, 1170)

    def der(k):
        return X[k] + BARRA

    def izq(k):
        return X[k] - BARRA

    def msg(y, de, a, texto, tipo="sincrona", cx=None):
        """Mensaje horizontal; el texto va encima de la línea (centrado en cx si se da)."""
        x_de = der(de) if X[a] > X[de] else izq(de)
        x_a = izq(a) if X[a] > X[de] else der(a)
        if tipo == "sincrona":
            L.flecha([(x_de, y), (x_a, y)], "llena")
        else:
            L.flecha([(x_de, y), (x_a, y)], "abierta", punteada=True)
        L.texto(cx if cx is not None else (x_de + x_a) / 2, y - 24, texto, fondo=True)

    entre_r_pr = (X["R"] + X["Pr"]) / 2  # etiquetas hacia rojas: entre dos líneas de vida

    msg(300, "U", "P", "solicitar_cita(paciente, profesional, fecha, hora)")
    msg(410, "P", "A", "c := agendar_cita(paciente, profesional, fecha, hora)")
    msg(520, "A", "R", "rojas := obtener_profesional(profesional, fecha)")
    msg(600, "R", "A", "rojas", "retorno")
    msg(710, "A", "Pr", "disponible := esta_disponible(fecha, hora)", cx=entre_r_pr)
    msg(790, "Pr", "A", "disponible", "retorno", cx=entre_r_pr)

    # [disponible]: creación de c:Cita a la altura de su cabecera
    L.flecha([(der("A"), y_create), (cab["C"][0], y_create)], "abierta", punteada=True)
    L.texto(
        (X["Pr"] + cab["C"][0]) / 2,
        y_create - 24,
        "«create» Cita(paciente, rojas, fecha, hora)",
        fondo=True,
    )
    msg(1110, "A", "Pr", "agregar_cita(c)", cx=entre_r_pr)
    msg(1210, "A", "R", "guardar_cita(c)")
    msg(1320, "A", "P", "c", "retorno")

    def automensaje(y1, y2, texto):
        barra("P", y1 - 10, y2 + 20, desp=10)
        xr = X["P"] + 10 + BARRA
        L.flecha([(xr, y1), (xr + 60, y1), (xr + 60, y2), (xr, y2)], "llena")
        L.texto(xr + 85, (y1 + y2) / 2, texto, anc="lm", fondo=True)

    automensaje(1400, 1455, 'mostrar_mensaje("Cita registrada")')

    # [else]: no existe c:Cita
    msg(1620, "A", "P", "BloqueNoDisponible", "retorno")
    automensaje(1700, 1755, 'mostrar_mensaje("Bloque no disponible")')
    return L.guardar("2-secuencia.png")


# =======================================================================================
# 3 · Diagrama de comunicación (sección 8 del contrato)
# =======================================================================================
def comunicacion():
    W, H = 3750, 1160
    L = Lienzo(W, H)
    cy = 600
    XU, XP, XA, XJ = 250, 1150, 2250, 3400
    yR, yC = cy - 400, cy + 400

    L.monigote(XU, cy)
    bp = L.caja_objeto(XP, cy, ":PantallaAgenda")
    ba = L.caja_objeto(XA, cy, "agenda:Agenda")
    br = L.caja_objeto(XA, yR, ":RepositorioAgenda")
    bj = L.caja_objeto(XJ, cy, "rojas:Profesional")
    bc = L.caja_objeto(XA, yC, "c:Cita")

    # enlaces (líneas continuas, sin flecha)
    L.linea([(XU + 42, cy), (bp[0], cy)])
    L.linea([(bp[2], cy), (ba[0], cy)])
    L.linea([(ba[2], cy), (bj[0], cy)])
    L.linea([(XA, br[3]), (XA, ba[1])])
    L.linea([(XA, ba[3]), (XA, bc[1])])
    # enlace reflexivo bajo :PantallaAgenda
    pata, prof = 52, 125
    L.linea(
        [
            (XP - pata, bp[3]),
            (XP - pata, bp[3] + prof),
            (XP + pata, bp[3] + prof),
            (XP + pata, bp[3]),
        ]
    )

    def etiqueta_h(cx, y, texto, hacia_derecha=True, debajo=False):
        """Etiqueta sobre (o bajo) un enlace horizontal, con flecha corta paralela."""
        dy_texto, dy_flecha = (46, 16) if not debajo else (-46, -16)
        L.texto(cx, y - dy_texto, texto, fondo=True)
        a, b = (cx - 45, cx + 45) if hacia_derecha else (cx + 45, cx - 45)
        L.flecha([(a, y - dy_flecha), (b, y - dy_flecha)], "abierta")

    def etiqueta_v(x, y, texto, hacia_abajo):
        """Etiqueta a la derecha de un enlace vertical con flecha corta paralela."""
        a, b = (y - 20, y + 20) if hacia_abajo else (y + 20, y - 20)
        L.flecha([(x + 24, a), (x + 24, b)], "abierta")
        L.texto(x + 50, y, texto, anc="lm", fondo=True)

    etiqueta_h((XU + 42 + bp[0]) / 2, cy, "1: solicitar_cita(paciente, profesional, fecha, hora)")
    etiqueta_h(
        (bp[2] + ba[0]) / 2, cy, "1.1: c := agendar_cita(paciente, profesional, fecha, hora)"
    )
    # Agenda -> Repositorio (hacia arriba): 1.1.1 y 1.1.5
    etiqueta_v(XA, 360, "1.1.1: rojas := obtener_profesional(profesional, fecha)", False)
    etiqueta_v(XA, 450, "1.1.5: [disponible] guardar_cita(c)", False)
    # Agenda -> Profesional (hacia la derecha): 1.1.2 sobre el enlace y 1.1.4 bajo él
    centro = (ba[2] + bj[0]) / 2
    etiqueta_h(centro, cy, "1.1.2: disponible := esta_disponible(fecha, hora)")
    etiqueta_h(centro, cy, "1.1.4: [disponible] agregar_cita(c)", debajo=True)
    # Agenda -> Cita (hacia abajo): 1.1.3
    etiqueta_v(XA, 840, "1.1.3: [disponible] «create» Cita(paciente, rojas, fecha, hora)", True)
    # automensajes de :PantallaAgenda
    xr, yb = XP + pata, bp[3]
    for y, texto in (
        (yb + 40, '1.2: [c registrada] mostrar_mensaje("Cita registrada")'),
        (yb + 95, '1.3: [BloqueNoDisponible] mostrar_mensaje("Bloque no disponible")'),
    ):
        L.flecha([(xr + 24, y - 18), (xr + 24, y + 18)], "abierta")
        L.texto(xr + 50, y, texto, anc="lm")
    return L.guardar("3-comunicacion.png")


# =======================================================================================
# 4 · Diagrama de clases (sección 4 del contrato)
# =======================================================================================
class Clase:
    """Clase UML de dos o tres compartimentos; mide su alto por el contenido."""

    def __init__(self, L, nombre, atributos, metodos, estereotipo=None, cursiva=False, maxw=760):
        self.L, self.nombre, self.est, self.cursiva = L, nombre, estereotipo, cursiva
        self.lh = L.tam + 10
        self.attrs = [x for a in atributos for x in self._partir(a, maxw)]
        self.mets = None if metodos is None else [x for m in metodos for x in self._partir(m, maxw)]
        cab = [nombre] + ([estereotipo] if estereotipo else [])
        anchos = [L.ancho(t, "b") for t in cab] + [L.ancho(t) for t in self.attrs]
        anchos += [L.ancho(t) for t in (self.mets or [])]
        self.w = int(max(anchos) + 40)
        self.h_cab = 20 + len(cab) * self.lh
        self.h_att = 20 + max(len(self.attrs), 1) * self.lh
        self.h_met = 0 if self.mets is None else 20 + max(len(self.mets), 1) * self.lh
        self.h = self.h_cab + self.h_att + self.h_met
        self.x = self.y = 0

    def _partir(self, texto, maxw):
        """Parte una firma larga en líneas de continuación, cortando en ', '."""
        if self.L.ancho(texto) <= maxw:
            return [texto]
        piezas = texto.split(", ")
        lineas, actual = [], ""
        for k, p in enumerate(piezas):
            trozo = p + ("," if k < len(piezas) - 1 else "")
            prueba = trozo if not actual else actual + " " + trozo
            if actual and self.L.ancho(("      " if lineas else "") + prueba) > maxw:
                lineas.append(actual)
                actual = trozo
            else:
                actual = prueba
        lineas.append(actual)
        return [lineas[0]] + ["      " + ln for ln in lineas[1:]]

    @property
    def x1(self):
        return self.x + self.w

    @property
    def y1(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    def dibujar(self):
        L, x, y, w = self.L, self.x, self.y, self.w
        L.rect(x, y, x + w, y + self.h)
        L.linea([(x, y + self.h_cab), (x + w, y + self.h_cab)])
        if self.mets is not None:
            ys = y + self.h_cab + self.h_att
            L.linea([(x, ys), (x + w, ys)])
        ty = y + 10 + self.lh / 2
        if self.est:
            L.texto(x + w / 2, ty, self.est, "n")
            ty += self.lh
        L.texto(x + w / 2, ty, self.nombre, "bi" if self.cursiva else "b")
        ty = y + self.h_cab + 10 + self.lh / 2
        for t in self.attrs:
            L.texto(x + 20, ty, t, "n", anc="lm")
            ty += self.lh
        if self.mets is not None:
            ty = y + self.h_cab + self.h_att + 10 + self.lh / 2
            for t in self.mets:
                L.texto(x + 20, ty, t, "n", anc="lm")
                ty += self.lh


def clases():
    L = Lienzo(10, 10, tam=28)  # solo para medir; se reemplaza por el lienzo definitivo

    agenda = Clase(
        L,
        "Agenda",
        ["- _repositorio: RepositorioAgenda"],
        [
            "+ Agenda(repositorio: RepositorioAgenda)",
            "+ registrar_profesional(nombre: str, especialidad: str): Profesional",
            "+ registrar_paciente(rut: str, nombre: str): Paciente",
            "+ registrar_franja(id_profesional: int, fecha: date, hora_inicio: time,"
            " hora_fin: time): FranjaHoraria",
            "+ agendar_cita(id_paciente: int, id_profesional: int, fecha: date, hora: time): Cita",
            "+ listar_profesionales(): list[Profesional]",
            "+ listar_pacientes(): list[Paciente]",
            "+ listar_citas(): list[Cita]",
            "+ comprobar(): None",
        ],
        maxw=820,
    )
    repo = Clase(
        L,
        "RepositorioAgenda",
        [],
        [
            "+ obtener_profesional(id_profesional: int, fecha: date): Profesional",
            "+ obtener_paciente(id_paciente: int): Paciente",
            "+ guardar_cita(cita: Cita): Cita",
            "+ guardar_profesional(profesional: Profesional): Profesional",
            "+ guardar_paciente(paciente: Paciente): Paciente",
            "+ guardar_franja(id_profesional: int, franja: FranjaHoraria): FranjaHoraria",
            "+ listar_profesionales(): list[Profesional]",
            "+ listar_pacientes(): list[Paciente]",
            "+ listar_citas(): list[Cita]",
            "+ comprobar(): None",
        ],
        estereotipo="«interface»",
        cursiva=True,
        maxw=820,
    )
    postgres = Clase(
        L,
        "RepositorioPostgres",
        ["- _dsn: str"],
        ["+ RepositorioPostgres(dsn: str)", "(realiza las 10 operaciones del puerto)"],
    )
    memoria = Clase(
        L,
        "RepositorioMemoria",
        [
            "- _profesionales: dict[int, Profesional]",
            "- _pacientes: dict[int, Paciente]",
            "- _franjas: dict[int, list[FranjaHoraria]]",
            "- _citas: list[Cita]",
        ],
        ["+ RepositorioMemoria()", "(realiza las 10 operaciones del puerto)"],
    )
    profesional = Clase(
        L,
        "Profesional",
        [
            "+ id: int",
            "+ nombre: str",
            "+ especialidad: str",
            "+ franjas: list[FranjaHoraria]",
            "+ citas: list[Cita]",
        ],
        [
            "+ Profesional(id: int, nombre: str, especialidad: str)",
            "+ esta_disponible(fecha: date, hora: time): bool",
            "+ agregar_cita(cita: Cita): None",
        ],
    )
    franja = Clase(
        L,
        "FranjaHoraria",
        ["+ fecha: date", "+ hora_inicio: time", "+ hora_fin: time"],
        [
            "+ FranjaHoraria(fecha: date, hora_inicio: time, hora_fin: time)",
            "+ contiene(hora: time): bool",
        ],
        maxw=560,
    )
    cita = Clase(
        L,
        "Cita",
        [
            "+ id: int | None",
            "+ paciente: Paciente",
            "+ profesional: Profesional",
            "+ fecha: date",
            "+ hora: time",
            "+ estado: EstadoCita",
        ],
        [
            "+ Cita(paciente: Paciente, profesional: Profesional, fecha: date, hora: time)",
            "+ esta_activa(): bool",
        ],
        maxw=560,
    )
    paciente = Clase(
        L,
        "Paciente",
        ["+ id: int", "+ rut: str", "+ nombre: str"],
        ["+ Paciente(id: int, rut: str, nombre: str)"],
        maxw=420,
    )
    estado = Clase(L, "EstadoCita", ["ACTIVA", "CANCELADA"], None, estereotipo="«enumeration»")

    # ---- posiciones -------------------------------------------------------------------
    M, TOP = 70, 110
    agenda.x, agenda.y = M, TOP
    repo.x, repo.y = agenda.x1 + 420, TOP
    postgres.x, postgres.y = repo.x1 + 380, TOP
    memoria.x, memoria.y = repo.x1 + 380, TOP + postgres.h + 120

    GAP = 330
    fila = max(agenda.y1, repo.y1, memoria.y1) + 250
    franja.x = M
    profesional.x = franja.x1 + GAP
    cita.x = profesional.x1 + GAP
    paciente.x = cita.x1 + GAP
    for c in (franja, profesional, cita, paciente):
        c.y = fila
    estado.x = cita.x + (cita.w - estado.w) / 2
    estado.y = max(cita.y1, profesional.y1) + 170

    W = int(max(paciente.x1, postgres.x1, memoria.x1) + M)
    H = int(max(estado.y1, profesional.y1) + M)
    L = Lienzo(W, H, tam=28)
    for c in (agenda, repo, postgres, memoria, profesional, franja, cita, paciente, estado):
        c.L = L  # las medidas se tomaron con un lienzo provisional
        c.dibujar()

    # ---- relaciones -------------------------------------------------------------------

    # Agenda ..> RepositorioAgenda (dependencia)
    ya = TOP + 60
    L.flecha([(agenda.x1, ya), (repo.x, ya)], "abierta", punteada=True)

    # RepositorioPostgres / RepositorioMemoria ..|> RepositorioAgenda (realización)
    for c, yy in ((postgres, TOP + 130), (memoria, memoria.y + 60)):
        tip, base = repo.x1, repo.x1 + 40
        L.linea([(c.x, yy), (base, yy)], punteada=True)
        L.poligono([(tip, yy), (base, yy - 22), (base, yy + 22)])

    # Profesional ◆— FranjaHoraria (composición: rombo negro en el extremo del todo)
    yl = fila + 70
    tip = profesional.x
    L.poligono([(tip, yl), (tip - 28, yl - 16), (tip - 56, yl), (tip - 28, yl + 16)], relleno=0)
    L.linea([(franja.x1, yl), (tip - 56, yl)])
    L.texto(franja.x1 + 12, yl - 24, "0..*", anc="lm")
    L.texto(franja.x1 + 12, yl + 26, "franjas", anc="lm")
    L.texto(tip - 66, yl - 24, "1", anc="rm")

    # Profesional — Cita (asociación bidireccional 1 — 0..*)
    L.linea([(profesional.x1, yl), (cita.x, yl)])
    L.texto(profesional.x1 + 12, yl - 24, "1", anc="lm")
    L.texto(profesional.x1 + 12, yl + 26, "profesional", anc="lm")
    L.texto(cita.x - 12, yl - 24, "0..*", anc="rm")
    L.texto(cita.x - 12, yl + 26, "citas", anc="rm")

    # Cita → Paciente (asociación navegable hacia Paciente)
    L.flecha([(cita.x1, yl), (paciente.x, yl)])
    L.texto(cita.x1 + 12, yl - 24, "0..*", anc="lm")
    L.texto(paciente.x - 28, yl - 24, "1", anc="rm")
    L.texto(paciente.x - 28, yl + 26, "paciente", anc="rm")

    # Cita → EstadoCita
    xe = cita.cx
    L.flecha([(xe, cita.y1), (xe, estado.y)])
    L.texto(xe + 16, cita.y1 + 30, "1", anc="lm")
    L.texto(xe + 16, estado.y - 36, "estado", anc="lm")
    return L.guardar("4-clases.png")


if __name__ == "__main__":
    for ruta in (actividades(), secuencia(), comunicacion(), clases()):
        print(ruta, Image.open(ruta).size)
