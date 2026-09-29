from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.lib.utils import ImageReader


# =========================================================
# CONFIGURACIÓN
# =========================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

BLUE = colors.HexColor("#17365D")
LIGHT_BLUE = colors.HexColor("#D9EAF7")
TABLE_HEADER = colors.HexColor("#D9D9D9")
TEXT_COLOR = colors.HexColor("#111827")


ASSETS_DIR = (
    Path(settings.BASE_DIR)
    / "core"
    / "assets"
    / "acta"
)

LOGO_PATH = (
    ASSETS_DIR
    / "logo_farmacias_similares.png"
)

WATERMARK_PATH = (
    ASSETS_DIR
    / "acta_marca_agua_simi.png"
)


# =========================================================
# HELPERS
# =========================================================

def _safe(value, default=""):
    if value is None:
        return default

    value = str(value).strip()

    return value if value else default


def _fecha_actual_espanol():
    meses = [
        "enero", "febrero", "marzo", "abril",
        "mayo", "junio", "julio", "agosto",
        "septiembre", "octubre", "noviembre", "diciembre",
    ]

    fecha = timezone.localdate()

    return (
        str(fecha.day),
        meses[fecha.month - 1],
        str(fecha.year),
    )


def _get_usuario_nombre(usuario):
    """
    Intenta obtener el nombre completo independientemente
    de cómo esté definido en el modelo.
    """

    nombre_completo = getattr(
        usuario,
        "nombre_completo",
        None,
    )

    if callable(nombre_completo):
        nombre_completo = nombre_completo()

    if nombre_completo:
        return str(nombre_completo).strip()

    nombre = getattr(usuario, "nombre", "")
    apellido = getattr(usuario, "apellido", "")

    nombre_armado = (
        f"{_safe(nombre)} {_safe(apellido)}"
    ).strip()

    if nombre_armado:
        return nombre_armado

    return _safe(
        getattr(usuario, "usuario_red", ""),
        "Sin nombre",
    )


def _get_equipos(usuario):
    """
    Obtiene los equipos relacionados al usuario.
    """

    equipos_relacion = getattr(
        usuario,
        "equipos",
        None,
    )

    if equipos_relacion is None:
        return []

    try:
        return list(equipos_relacion.all())
    except AttributeError:
        try:
            return list(equipos_relacion)
        except TypeError:
            return []


def _format_tipo_equipo(tipo):
    """
    Normaliza códigos antiguos y nombres de tipos.
    """

    tipo = _safe(tipo, "Equipo")

    mapping = {
        "NTBK": "Notebook",
        "NOTEBOOK": "Notebook",
        "CEL": "Celular",
        "CELULAR": "Celular",
        "TBIT": "Tablet",
        "TABLET": "Tablet",
        "BAM": "BAM / Router",
        "MAC": "Mac",
        "MONITOR": "Monitor",
        "ADAPTADOR": "Adaptador",
        "AUDIFONOS": "Audífonos",
        "AUDÍFONOS": "Audífonos",
        "TECLADO": "Teclado",
        "MOUSE": "Mouse",
        "DOCKING": "Docking",
    }

    key = tipo.upper().strip()

    return mapping.get(key, tipo)


def _nomenclatura(equipo):
    tipo = _format_tipo_equipo(
        getattr(equipo, "tipo", "")
    )

    marca = _safe(
        getattr(equipo, "marca", "")
    )

    modelo = _safe(
        getattr(equipo, "modelo", "")
    )

    partes = [
        parte
        for parte in [
            tipo,
            marca,
            modelo,
        ]
        if parte
    ]

    return " ".join(partes)


def _get_estado_equipo(equipo):
    estado = getattr(
        equipo,
        "estado",
        None,
    )

    if estado is None:
        return ""

    if hasattr(
        equipo,
        "get_estado_display",
    ):
        try:
            return equipo.get_estado_display()
        except Exception:
            pass

    return _safe(estado)


def _get_accesorios(equipo):
    return _safe(
        getattr(
            equipo,
            "accesorios",
            ""
        ),
        "Sin accesorios"
    )


# =========================================================
# ENCABEZADO / MARCA DE AGUA
# =========================================================

def _draw_page_background(canvas, doc):
    canvas.saveState()

    # -----------------------------------------------------
    # MARCA DE AGUA
    # -----------------------------------------------------

    if WATERMARK_PATH.exists():
        try:
            watermark = ImageReader(
                str(WATERMARK_PATH)
            )

            watermark_size = 17.5 * cm

            x = (
                PAGE_WIDTH
                - watermark_size
            ) / 2

            y = 2.6 * cm

            canvas.setFillAlpha(0.12)

            canvas.drawImage(
                watermark,
                x,
                y,
                width=watermark_size,
                height=watermark_size,
                preserveAspectRatio=True,
                mask="auto",
            )

            canvas.setFillAlpha(1)

        except Exception:
            pass

    # -----------------------------------------------------
    # LOGO
    # -----------------------------------------------------

    if LOGO_PATH.exists():
        try:
            logo = ImageReader(
                str(LOGO_PATH)
            )

            canvas.drawImage(
                logo,
                1.35 * cm,
                PAGE_HEIGHT - 2.0 * cm,
                width=7.0 * cm,
                height=1.5 * cm,
                preserveAspectRatio=True,
                anchor="sw",
                mask="auto",
            )

        except Exception:
            pass

    # -----------------------------------------------------
    # EJEMPLAR
    # -----------------------------------------------------

    canvas.setFillColor(BLUE)
    canvas.setFont(
        "Helvetica-Bold",
        10,
    )

    canvas.drawRightString(
        PAGE_WIDTH - 1.4 * cm,
        PAGE_HEIGHT - 1.1 * cm,
        "EJEMPLAR ____/____",
    )

    # -----------------------------------------------------
    # DEPARTAMENTO
    # -----------------------------------------------------

    canvas.setFont(
        "Helvetica-Bold",
        10,
    )

    canvas.drawString(
        1.35 * cm,
        PAGE_HEIGHT - 2.35 * cm,
        "DEPARTAMENTO DE TECNOLOGÍA / "
        "INFRAESTRUCTURA TI CHILE",
    )

    canvas.drawString(
        1.35 * cm,
        PAGE_HEIGHT - 2.75 * cm,
        "Camino Lo Echevers #550, "
        "Módulo 16, 17 y 18, Quilicura, Santiago.",
    )

    # -----------------------------------------------------
    # MARCO DEL DOCUMENTO
    # -----------------------------------------------------

    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.8)
    canvas.roundRect(
        1.05 * cm,
        1.05 * cm,
        PAGE_WIDTH - 2.10 * cm,
        PAGE_HEIGHT - 4.15 * cm,
        0.18 * cm,
        stroke=1,
        fill=0,
    )

    # -----------------------------------------------------
    # NÚMERO DE PÁGINA
    # -----------------------------------------------------

    canvas.setFillColor(
        colors.HexColor("#333333")
    )

    canvas.setFont(
        "Helvetica",
        9,
    )

    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        0.65 * cm,
        str(doc.page),
    )

    canvas.restoreState()


# =========================================================
# ESTILOS
# =========================================================

def _build_styles():
    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "ActaTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=12,
    )

    body = ParagraphStyle(
        "ActaBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.4,
        leading=15.2,
        alignment=TA_LEFT,
        textColor=TEXT_COLOR,
    )

    body_bold = ParagraphStyle(
        "ActaBodyBold",
        parent=body,
        fontName="Helvetica-Bold",
    )

    table_header = ParagraphStyle(
        "ActaTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.6,
        leading=10.2,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    table_cell = ParagraphStyle(
        "ActaTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.1,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    table_center = ParagraphStyle(
        "ActaTableCenter",
        parent=table_cell,
        alignment=TA_CENTER,
    )

    note_title = ParagraphStyle(
        "ActaNoteTitle",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=10.2,
        spaceAfter=5,
    )

    signature = ParagraphStyle(
        "ActaSignature",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.6,
        leading=11.8,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    signature_bold = ParagraphStyle(
        "ActaSignatureBold",
        parent=signature,
        fontName="Helvetica-Bold",
    )

    return {
        "title": title,
        "body": body,
        "body_bold": body_bold,
        "table_header": table_header,
        "table_cell": table_cell,
        "table_center": table_center,
        "note_title": note_title,
        "signature": signature,
        "signature_bold": signature_bold,
    }


# =========================================================
# TABLA EQUIPOS
# =========================================================

def _build_equipment_table(
    usuario,
    styles,
):
    equipos = _get_equipos(usuario)

    headers = [
        Paragraph(
            "N.º<br/>Orden",
            styles["table_header"],
        ),
        Paragraph(
            "Nomenclatura",
            styles["table_header"],
        ),
        Paragraph(
            "Accesorios",
            styles["table_header"],
        ),
        Paragraph(
            "N.º Serie",
            styles["table_header"],
        ),
        Paragraph(
            "N.º Activo fijo",
            styles["table_header"],
        ),
        Paragraph(
            "Estado",
            styles["table_header"],
        ),
    ]

    data = [headers]

    if not equipos:
        data.append(
            [
                Paragraph(
                    "1",
                    styles["table_center"],
                ),
                Paragraph(
                    "Sin equipos asignados",
                    styles["table_cell"],
                ),
                "",
                "",
                "",
                "",
            ]
        )

    else:
        for index, equipo in enumerate(
            equipos,
            start=1,
        ):
            data.append(
                [
                    Paragraph(
                        str(index),
                        styles["table_center"],
                    ),

                    Paragraph(
                        _nomenclatura(equipo),
                        styles["table_cell"],
                    ),

                    Paragraph(
                        _get_accesorios(equipo),
                        styles["table_cell"],
                    ),

                    Paragraph(
                        _safe(
                            getattr(
                                equipo,
                                "numero_serie",
                                "",
                            )
                        ),
                        styles["table_cell"],
                    ),

                    Paragraph(
                        _safe(
                            getattr(
                                equipo,
                                "af",
                                "",
                            )
                        ),
                        styles["table_cell"],
                    ),

                    Paragraph(
                        _get_estado_equipo(
                            equipo
                        ),
                        styles["table_center"],
                    ),
                ]
            )

    table = Table(
        data,
        colWidths=[
            1.25 * cm,
            4.2 * cm,
            2.6 * cm,
            3.2 * cm,
            3.2 * cm,
            2.1 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    TABLE_HEADER,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, -1),
                    colors.black,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor(
                        "#444444"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (0, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (-1, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# =========================================================
# FIRMAS
# =========================================================

def _build_signatures(
    usuario,
    entregado_por,
    styles,
):
    area = _safe(
        getattr(
            usuario,
            "dpto_area",
            "",
        ),
        "DEPARTAMENTO / ÁREA",
    )

    entregado_por = _safe(
        entregado_por,
        "____________________________",
    )

    left = [
        Paragraph(
            "ENTREGUÉ",
            styles["signature_bold"],
        ),
        Spacer(1, 1.15 * cm),
        Paragraph(
            entregado_por,
            styles["signature"],
        ),
        Paragraph(
            "INFRAESTRUCTURA TI",
            styles["signature_bold"],
        ),
    ]

    right = [
        Paragraph(
            "RECIBÍ",
            styles["signature_bold"],
        ),
        Spacer(1, 1.15 * cm),
        Paragraph(
            "____________________________",
            styles["signature"],
        ),
        Paragraph(
            area.upper(),
            styles["signature_bold"],
        ),
    ]

    firmas = Table(
        [
            [
                left,
                right,
            ]
        ],
        colWidths=[
            8.3 * cm,
            8.3 * cm,
        ],
        hAlign="CENTER",
    )

    firmas.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    vb = [
        Spacer(1, 0.45 * cm),

        Paragraph(
            "V° B°",
            styles["signature"],
        ),

        Spacer(1, 1.1 * cm),

        Paragraph(
            "VICTOR GARRIDO ALARCÓN",
            styles["signature"],
        ),

        Paragraph(
            "COORDINADOR INFRAESTRUCTURA TI",
            styles["signature"],
        ),
    ]

    return firmas, vb


# =========================================================
# GENERADOR PRINCIPAL
# =========================================================

def generar_acta_entrega_pdf(
    usuario,
    entregado_por="",
):
    """
    Genera un Acta de Entrega en PDF.

    Retorna:
        BytesIO
    """

    buffer = BytesIO()

    styles = _build_styles()

    # -----------------------------------------------------
    # DOCUMENTO
    # -----------------------------------------------------

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.35 * cm,
        rightMargin=1.35 * cm,
        topMargin=3.35 * cm,
        bottomMargin=1.25 * cm,
        title=(
            "Acta de Entrega de "
            "Equipamiento Tecnológico"
        ),
        author=(
            "Infraestructura TI Chile"
        ),
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="acta_frame",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    template = PageTemplate(
        id="acta_template",
        frames=[frame],
        onPage=_draw_page_background,
    )

    doc.addPageTemplates(
        [template]
    )

    story = []

    # -----------------------------------------------------
    # TÍTULO
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "ACTA DE ENTREGA DE "
            "EQUIPAMIENTO TECNOLÓGICO",
            styles["title"],
        )
    )

    story.append(
        Spacer(
            1,
            0.15 * cm,
        )
    )

    # -----------------------------------------------------
    # TEXTO INTRODUCTORIO
    # -----------------------------------------------------

    nombre_usuario = (
        _get_usuario_nombre(usuario)
    )

    area_usuario = _safe(
        getattr(
            usuario,
            "dpto_area",
            "",
        ),
        "________________________",
    )

    dia_actual, mes_actual, anio_actual = _fecha_actual_espanol()

    intro = (
        f"En Quilicura, a {dia_actual} días del mes "
        f"de {mes_actual} de {anio_actual}, "
        "Farmacias de Similares Chile S.A. "
        "RUT 59.111.330-5, a través del "
        "Departamento de Tecnología, procede "
        "a hacer entrega al colaborador "
        f"<b>{nombre_usuario}</b>, "
        "Rut ___________________-_____, "
        "perteneciente al Departamento de "
        f"<b>{area_usuario}</b>, "
        "del/los siguiente(s) elemento(s) "
        "y como parte de la asignación de "
        "recursos para el cumplimiento de "
        "sus funciones, según el siguiente "
        "detalle:"
    )

    story.append(
        Paragraph(
            intro,
            styles["body"],
        )
    )

    story.append(
        Spacer(
            1,
            0.35 * cm,
        )
    )

    # -----------------------------------------------------
    # TABLA
    # -----------------------------------------------------

    story.append(
        _build_equipment_table(
            usuario,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            0.35 * cm,
        )
    )

    # -----------------------------------------------------
    # NOTA
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Nota:",
            styles["note_title"],
        )
    )

    note = (
        "El equipo y/o accesorios quedan "
        "en custodia, cuidado y responsabilidad "
        "del Trabajador, el que deberá ser "
        "devuelto sin daños y con todos los "
        "accesorios entregados al término de "
        "la relación laboral o cuando la "
        "organización así lo requiera."
    )

    story.append(
        Paragraph(
            note,
            styles["body"],
        )
    )

    story.append(
        Spacer(
            1,
            0.55 * cm,
        )
    )

    # -----------------------------------------------------
    # FIRMAS
    # -----------------------------------------------------

    firmas, vb = _build_signatures(
        usuario,
        entregado_por,
        styles,
    )

    signatures_block = [
        firmas,
        *vb,
    ]

    story.append(
        KeepTogether(
            signatures_block
        )
    )

    # -----------------------------------------------------
    # GENERACIÓN
    # -----------------------------------------------------

    doc.build(story)

    buffer.seek(0)

    return buffer

def generar_acta_custodia_pdf(snapshot):
    """Render a historical acta strictly from its persisted, immutable snapshot."""
    from xml.sax.saxutils import escape
    from reportlab.platypus import SimpleDocTemplate

    def plain(value, fallback='—'):
        value = str(value or '').strip()
        return escape(value) if value else fallback

    def row(label, value):
        return [Paragraph(f'<b>{plain(label)}</b>', small), Paragraph(plain(value), small)]

    colaborador = snapshot.get('colaborador') or {}
    activo = snapshot.get('activo') or {}
    operador = snapshot.get('usuario_ti') or {}
    accesorios = snapshot.get('accesorios') or []
    fecha = snapshot.get('fecha_emision', '')[:10]
    fecha = '/'.join(reversed(fecha.split('-'))) if len(fecha) == 10 else fecha
    tipo = snapshot.get('tipo_movimiento') or ''
    title_style = ParagraphStyle('ItamTitle', fontName='Helvetica-Bold', fontSize=12,
                                 leading=15, alignment=TA_CENTER, spaceAfter=11)
    heading = ParagraphStyle('ItamHeading', fontName='Helvetica-Bold', fontSize=9,
                             leading=12, textColor=BLUE, spaceBefore=10, spaceAfter=5)
    small = ParagraphStyle('ItamText', fontName='Helvetica', fontSize=8.5, leading=11,
                           textColor=TEXT_COLOR, wordWrap='CJK')
    custody = tipo in {'ASIGNACION', 'REASIGNACION', 'PRESTAMO', 'CAMBIO'}
    title = 'ACTA DE ASIGNACIÓN Y CUSTODIA DE ACTIVO TI' if custody else 'ACTA DE MOVIMIENTO DE ACTIVO TI'
    story = [Paragraph(title, title_style)]
    story.append(Paragraph(f"<b>Folio:</b> {plain(snapshot.get('folio'))} &nbsp;&nbsp; "
                           f"<b>Fecha:</b> {plain(fecha)} &nbsp;&nbsp; "
                           f"<b>Movimiento:</b> {plain(tipo)}", small))
    story.append(Paragraph(f"<b>Ubicación:</b> {plain(snapshot.get('ubicacion_destino'))}", small))
    if snapshot.get('operacion_id'):
        story.append(Paragraph(f"<b>Cambio de equipo:</b> {plain(snapshot['operacion_id'])}", small))
    if colaborador:
        story.append(Paragraph('DATOS DEL COLABORADOR', heading))
        col_rows = [
            row('Nombre', colaborador.get('nombre_completo')),
            row('RUT', colaborador.get('rut')),
            row('Área / cargo', f"{colaborador.get('area') or ''} / {colaborador.get('cargo') or ''}"),
            row('Correo', colaborador.get('correo_corp')),
            row('Ubicación', colaborador.get('ubicacion')),
        ]
        if tipo == 'REASIGNACION':
            previous = snapshot.get('colaborador_origen') or {}
            col_rows.append(row('Custodio anterior', previous.get('nombre_completo')))
        col_table = Table(col_rows, colWidths=[3.2 * cm, 14.6 * cm], hAlign='LEFT')
        col_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                       ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                       ('TOPPADDING', (0, 0), (-1, -1), 2)]))
        story.append(col_table)
    else:
        story.append(Paragraph('Custodia: Inventario TI (sin colaborador asignado).', small))
    story.append(Paragraph('DATOS DEL ACTIVO', heading))
    activo_rows = [
        row('Tipo / marca / modelo', ' / '.join(str(activo.get(k) or '') for k in ('tipo', 'marca', 'modelo'))),
        row('Serie / activo fijo', f"{activo.get('numero_serie') or '—'} / {activo.get('af') or '—'}"),
    ]
    for key, label in (('imei', 'IMEI'), ('mac_address', 'MAC'), ('hostname', 'Hostname')):
        if activo.get(key):
            activo_rows.append(row(label, activo[key]))
    activo_rows.extend([
        row('Estado físico', snapshot.get('estado_fisico')),
        row('Estado operativo', snapshot.get('estado_operativo_resultante')),
        row('Accesorios', ', '.join(
            f"{a.get('nombre', '')}{' (faltante: ' + a.get('nota', '') + ')' if not a.get('entregado') else ''}"
            for a in accesorios) or 'Sin accesorios registrados'),
        row('Observaciones', snapshot.get('observaciones')),
    ])
    activo_table = Table(activo_rows, colWidths=[3.2 * cm, 14.6 * cm], hAlign='LEFT')
    activo_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                     ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                     ('TOPPADDING', (0, 0), (-1, -1), 2)]))
    story.append(activo_table)
    if custody:
        story.append(Paragraph('CONDICIÓN DE CUSTODIA', heading))
        story.append(Paragraph(
            'El colaborador recibe el activo y sus accesorios en el estado señalado. '
            'Se responsabiliza de su cuidado y buen uso, y se compromete a devolverlos '
            'cuando la organización lo solicite, ante un cambio de funciones o al '
            'término de la relación laboral.', small))
        entrega_nombre = operador.get('nombre')
        recibe_nombre = colaborador.get('nombre_completo')
        entrega_label, recibe_label = 'Entrega', 'Recibe'
    elif tipo in {'DEVOLUCION', 'INGRESO_REPARACION'} and colaborador:
        story.append(Paragraph('CONSTANCIA DEL MOVIMIENTO', heading))
        story.append(Paragraph('Se deja constancia de la recepción del activo por Infraestructura TI en el estado y con los accesorios indicados.', small))
        entrega_nombre = colaborador.get('nombre_completo')
        recibe_nombre = operador.get('nombre')
        entrega_label, recibe_label = 'Entrega', 'Recibe TI'
    else:
        story.append(Paragraph('CONSTANCIA DEL MOVIMIENTO', heading))
        story.append(Paragraph('Infraestructura TI registra el cambio de estado y ubicación del activo con las observaciones indicadas.', small))
        entrega_nombre = operador.get('nombre')
        recibe_nombre = ''
        entrega_label, recibe_label = 'Registra TI', 'Verifica'
    story.append(Spacer(1, 1.0 * cm))
    firmas = Table([[
        Paragraph(f"________________________<br/><b>{entrega_label}</b><br/>{plain(entrega_nombre)}", small),
        Paragraph(f"________________________<br/><b>{recibe_label}</b><br/>{plain(recibe_nombre)}", small),
        Paragraph('________________________<br/><b>V°B°</b><br/>Nombre y firma', small),
    ]], colWidths=[5.95 * cm] * 3)
    firmas.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    story.append(firmas)
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.6 * cm,
                                 rightMargin=1.6 * cm, topMargin=3.2 * cm,
                                 bottomMargin=1.8 * cm,
                                 title=f"{title} {snapshot.get('folio', '')}")
    document.build(story, onFirstPage=_draw_page_background,
                   onLaterPages=_draw_page_background)
    buffer.seek(0)
    return buffer
