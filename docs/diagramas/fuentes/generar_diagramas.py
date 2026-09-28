"""Genera los diagramas técnicos del portal en PNG y SVG.

El script no consulta la base de datos ni requiere servicios externos. Las
coordenadas y textos se mantienen aquí para que los diagramas sean
reproducibles junto con sus fuentes Mermaid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]

COLORS = {
    "ink": "#10213D",
    "muted": "#52647F",
    "line": "#7F93B2",
    "blue": "#2563EB",
    "blue_fill": "#EAF2FF",
    "green": "#138A50",
    "green_fill": "#E6F7EE",
    "amber": "#C46A08",
    "amber_fill": "#FFF5DF",
    "red": "#C9363E",
    "red_fill": "#FDECEE",
    "violet": "#6D45C7",
    "violet_fill": "#F1ECFF",
    "slate": "#56657A",
    "slate_fill": "#F1F5F9",
    "white": "#FFFFFF",
    "canvas": "#F8FAFD",
    "group": "#EDF3FA",
}


@dataclass
class Group:
    x: int
    y: int
    w: int
    h: int
    title: str
    fill: str = "#F3F7FC"


@dataclass
class Node:
    key: str
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: list[str] = field(default_factory=list)
    tone: str = "blue"
    small: bool = False


@dataclass
class Edge:
    points: list[tuple[int, int]]
    label: str = ""
    label_at: tuple[int, int] | None = None
    tone: str = "line"
    dashed: bool = False


@dataclass
class Diagram:
    filename: str
    width: int
    height: int
    title: str
    subtitle: str
    groups: list[Group]
    nodes: list[Node]
    edges: list[Edge]
    footer: str


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu")
        / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _tone(tone: str) -> tuple[str, str]:
    return COLORS[f"{tone}_fill"], COLORS[tone]


def _arrow_head(start: tuple[int, int], end: tuple[int, int], length=18, width=10):
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    back_x = end[0] - length * math.cos(angle)
    back_y = end[1] - length * math.sin(angle)
    return [
        end,
        (
            int(back_x + width * math.sin(angle)),
            int(back_y - width * math.cos(angle)),
        ),
        (
            int(back_x - width * math.sin(angle)),
            int(back_y + width * math.cos(angle)),
        ),
    ]


def render_png(diagram: Diagram):
    image = Image.new("RGB", (diagram.width, diagram.height), COLORS["canvas"])
    draw = ImageDraw.Draw(image)

    draw.text((70, 42), diagram.title, fill=COLORS["ink"], font=_font(46, True))
    draw.text((72, 105), diagram.subtitle, fill=COLORS["muted"], font=_font(25))

    for group in diagram.groups:
        draw.rounded_rectangle(
            (group.x, group.y, group.x + group.w, group.y + group.h),
            radius=24,
            fill=group.fill,
            outline="#D5E0EE",
            width=3,
        )
        draw.text(
            (group.x + 24, group.y + 16),
            group.title.upper(),
            fill=COLORS["muted"],
            font=_font(21, True),
        )

    for edge in diagram.edges:
        color = COLORS.get(edge.tone, edge.tone)
        if edge.dashed:
            for a, b in zip(edge.points, edge.points[1:]):
                distance = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                steps = max(1, distance // 18)
                for index in range(0, steps, 2):
                    t1 = index / steps
                    t2 = min((index + 1) / steps, 1)
                    p1 = (int(a[0] + (b[0] - a[0]) * t1), int(a[1] + (b[1] - a[1]) * t1))
                    p2 = (int(a[0] + (b[0] - a[0]) * t2), int(a[1] + (b[1] - a[1]) * t2))
                    draw.line([p1, p2], fill=color, width=5)
        else:
            draw.line(edge.points, fill=color, width=5, joint="curve")
        draw.polygon(_arrow_head(edge.points[-2], edge.points[-1]), fill=color)
        if edge.label and edge.label_at:
            bbox = draw.textbbox((0, 0), edge.label, font=_font(19, True))
            x, y = edge.label_at
            pad = 9
            draw.rounded_rectangle(
                (x - pad, y - pad, x + bbox[2] + pad, y + bbox[3] + pad),
                radius=8,
                fill=COLORS["white"],
                outline="#D6E0EC",
            )
            draw.text((x, y), edge.label, fill=color, font=_font(19, True))

    for node in diagram.nodes:
        fill, outline = _tone(node.tone)
        draw.rounded_rectangle(
            (node.x, node.y, node.x + node.w, node.y + node.h),
            radius=20,
            fill=fill,
            outline=outline,
            width=4,
        )
        title_size = 23 if node.small else 27
        body_size = 18 if node.small else 21
        draw.text(
            (node.x + 22, node.y + 19),
            node.title,
            fill=COLORS["ink"],
            font=_font(title_size, True),
        )
        line_y = node.y + (64 if node.small else 70)
        for line in node.lines:
            draw.text(
                (node.x + 22, line_y),
                line,
                fill=COLORS["muted"],
                font=_font(body_size),
            )
            line_y += body_size + 12

    draw.text(
        (70, diagram.height - 50),
        diagram.footer,
        fill=COLORS["muted"],
        font=_font(18),
    )
    image.save(ROOT / f"{diagram.filename}.png", optimize=True)


def _svg_text(x, y, value, size, color, bold=False):
    weight = "700" if bold else "400"
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">'
        f"{escape(value)}</text>"
    )


def render_svg(diagram: Diagram):
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{diagram.width}" '
        f'height="{diagram.height}" viewBox="0 0 {diagram.width} {diagram.height}">',
        "<defs>",
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">',
        '<feDropShadow dx="0" dy="5" stdDeviation="6" flood-opacity="0.10"/>',
        "</filter>",
        "</defs>",
        f'<rect width="100%" height="100%" fill="{COLORS["canvas"]}"/>',
        _svg_text(70, 78, diagram.title, 46, COLORS["ink"], True),
        _svg_text(72, 126, diagram.subtitle, 25, COLORS["muted"]),
    ]

    for group in diagram.groups:
        parts.append(
            f'<rect x="{group.x}" y="{group.y}" width="{group.w}" height="{group.h}" '
            f'rx="24" fill="{group.fill}" stroke="#D5E0EE" stroke-width="3"/>'
        )
        parts.append(
            _svg_text(group.x + 24, group.y + 42, group.title.upper(), 21, COLORS["muted"], True)
        )

    for edge in diagram.edges:
        color = COLORS.get(edge.tone, edge.tone)
        points = " ".join(f"{x},{y}" for x, y in edge.points)
        dash = ' stroke-dasharray="14 12"' if edge.dashed else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="5" stroke-linejoin="round" stroke-linecap="round"{dash}/>'
        )
        head = " ".join(
            f"{x},{y}" for x, y in _arrow_head(edge.points[-2], edge.points[-1])
        )
        parts.append(f'<polygon points="{head}" fill="{color}"/>')
        if edge.label and edge.label_at:
            x, y = edge.label_at
            width = max(70, len(edge.label) * 11 + 18)
            parts.append(
                f'<rect x="{x - 9}" y="{y - 25}" width="{width}" height="35" '
                'rx="8" fill="#FFFFFF" stroke="#D6E0EC"/>'
            )
            parts.append(_svg_text(x, y, edge.label, 19, color, True))

    for node in diagram.nodes:
        fill, outline = _tone(node.tone)
        parts.append(
            f'<rect x="{node.x}" y="{node.y}" width="{node.w}" height="{node.h}" '
            f'rx="20" fill="{fill}" stroke="{outline}" stroke-width="4" filter="url(#shadow)"/>'
        )
        title_size = 23 if node.small else 27
        body_size = 18 if node.small else 21
        parts.append(
            _svg_text(node.x + 22, node.y + 46, node.title, title_size, COLORS["ink"], True)
        )
        line_y = node.y + (88 if node.small else 96)
        for line in node.lines:
            parts.append(_svg_text(node.x + 22, line_y, line, body_size, COLORS["muted"]))
            line_y += body_size + 12

    parts.append(
        _svg_text(70, diagram.height - 25, diagram.footer, 18, COLORS["muted"])
    )
    parts.append("</svg>")
    (ROOT / f"{diagram.filename}.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def general_flow():
    groups = [
        Group(60, 165, 2680, 360, "Cliente, autenticación y sesión", "#EFF5FF"),
        Group(60, 555, 2680, 390, "API y reglas de negocio", "#F5F7FB"),
        Group(60, 975, 2680, 285, "Módulos del portal", "#F4F8F6"),
        Group(60, 1290, 2680, 300, "Persistencia, trazabilidad y operación", "#F8F5FF"),
    ]
    nodes = [
        Node("ui", 120, 245, 380, 190, "React + Vite", ["Sidebar y vistas", "Formularios responsivos", "Axios centralizado"]),
        Node("login", 585, 245, 380, 190, "Inicio de sesión", ["Credenciales + CSRF", "Limitación de intentos", "Respuesta sin secretos"]),
        Node("jwt", 1050, 245, 390, 190, "JWT", ["Access token en memoria", "Refresh en cookie HttpOnly", "Rotación y lista de bloqueo"], "violet"),
        Node("session", 1525, 245, 410, 190, "PortalSession", ["Identificador sid único", "Actividad validada en servidor", "Sesión revocable"], "violet"),
        Node("idle", 2020, 245, 650, 190, "Inactividad efectiva", ["Eventos reales del navegador", "Timeout predeterminado: 5 minutos", "Recargar conserva una sesión vigente"], "amber"),
        Node("api", 120, 650, 350, 190, "API REST", ["Endpoints por módulo", "Paginación y filtros", "Respuestas JSON"]),
        Node("auth", 555, 650, 380, 190, "Autenticación", ["Valida JWT, sid y CSRF", "Rechaza sesión expirada", "Asocia usuario autenticado"], "violet"),
        Node("roles", 1020, 650, 390, 190, "Permisos por rol", ["Visualizador", "Operador Infraestructura", "Administrador"], "amber"),
        Node("rules", 1495, 650, 480, 190, "Serializers + servicios", ["Validaciones de dominio", "Asignaciones centralizadas", "Cifrado y revelado controlado"], "green"),
        Node("tx", 2060, 650, 610, 190, "Transacciones", ["transaction.atomic()", "Bloqueo select_for_update()", "Rollback ante cualquier fallo"], "green"),
        Node("users", 105, 1050, 330, 130, "Usuarios", ["Ficha, estado y acta"], "blue", True),
        Node("assets", 475, 1050, 330, 130, "Equipos", ["Notebook, celular y más"], "blue", True),
        Node("ips", 845, 1050, 330, 130, "Gestión de IP", ["Segmentos y asignación"], "blue", True),
        Node("phone", 1215, 1050, 330, 130, "Anexos", ["Disponibles o asignados"], "blue", True),
        Node("server", 1585, 1050, 330, 130, "Servidores", ["IP del segmento permitido"], "blue", True),
        Node("profile", 1955, 1050, 330, 130, "Perfiles", ["Credenciales cifradas"], "blue", True),
        Node("pc", 2325, 1050, 330, 130, "PCs genéricos", ["Organización e IP"], "blue", True),
        Node("mysql", 170, 1380, 570, 145, "MySQL 8", ["utf8mb4 · modo estricto", "Índices, FK y restricciones"], "green"),
        Node("history", 890, 1380, 650, 145, "Historial funcional", ["Quién, cuándo, módulo y cambio", "Usuario, equipos, IP, anexos y más"], "violet"),
        Node("audit", 1690, 1380, 470, 145, "Auditoría de seguridad", ["Revelado de secretos", "Request ID y eventos sensibles"], "red"),
        Node("ops", 2310, 1380, 360, 145, "Operación", ["Logs JSON", "Backups y monitoreo"], "slate"),
    ]
    edges = [
        Edge([(500, 340), (585, 340)]),
        Edge([(965, 340), (1050, 340)]),
        Edge([(1440, 340), (1525, 340)]),
        Edge([(1935, 340), (2020, 340)]),
        Edge([(310, 435), (310, 650)], "HTTPS", (325, 550), "blue"),
        Edge([(470, 745), (555, 745)]),
        Edge([(935, 745), (1020, 745)]),
        Edge([(1410, 745), (1495, 745)]),
        Edge([(1975, 745), (2060, 745)]),
        Edge([(2365, 840), (2365, 900), (1375, 900), (1375, 975)], "operación válida", (1760, 890), "green"),
        Edge([(1375, 1260), (1375, 1335), (455, 1335), (455, 1380)], "persistir", (880, 1323), "green"),
        Edge([(1375, 1260), (1375, 1380)], "trazar", (1390, 1323), "violet"),
        Edge([(1735, 1260), (1735, 1380)], "auditar", (1750, 1323), "red", True),
        Edge([(2160, 1452), (2310, 1452)], "eventos", (2175, 1438), "slate"),
    ]
    return Diagram(
        "flujo_sistema_general",
        2800,
        1650,
        "Portal Infraestructura TI — Flujo general",
        "Recorrido de una acción desde la interfaz hasta la persistencia y su trazabilidad",
        groups,
        nodes,
        edges,
        "Fuente: implementación Django/DRF + React del repositorio · Actualizado: 28-09-2026",
    )


def user_state_flow():
    groups = [
        Group(60, 165, 2480, 330, "Edición y confirmación", "#EFF5FF"),
        Group(60, 525, 2480, 540, "Efectos según el estado del usuario", "#F7F9FC"),
        Group(60, 1095, 2480, 410, "Ficha y emisión del acta", "#F4F8F6"),
    ]
    nodes = [
        Node("edit", 120, 245, 420, 165, "Editar usuario", ["Cambiar datos, estado", "o relaciones permitidas"]),
        Node("confirm", 720, 245, 480, 165, "Advertencia previa", ["Explica efectos del estado", "y solicita confirmación"], "amber"),
        Node("save", 1380, 245, 460, 165, "Guardar en transacción", ["Validar restricciones", "Aplicar el cambio completo"], "green"),
        Node("history", 2020, 245, 440, 165, "Registrar historial", ["Actor, fecha y origen", "Valores anterior y actual"], "violet"),
        Node("active", 130, 615, 620, 330, "ACTIVO", ["Puede mantener o recibir IP", "Puede mantener equipos", "Puede mantener anexo", "Las asignaciones se sincronizan"], "green"),
        Node("leave", 970, 615, 620, 330, "LICENCIA MÉDICA", ["Libera solamente la IP", "Conserva equipos asignados", "Conserva anexo asignado", "Registra la liberación en historial"], "amber"),
        Node("down", 1810, 615, 620, 330, "BAJA", ["Libera la IP", "Desasigna equipos", "Libera el anexo", "Solicita validar devolución física"], "red"),
        Node("record", 120, 1185, 390, 175, "Abrir ficha", ["El usuario solicita", "crear acta de entrega"]),
        Node("has", 680, 1185, 520, 175, "Validar equipos", ["¿Existe al menos un equipo", "actualmente asignado?"], "amber"),
        Node("deny", 1390, 1160, 500, 200, "No se puede emitir", ["Respuesta HTTP 409", "Mensaje explica que el usuario", "no posee equipos asignados"], "red"),
        Node("pdf", 2050, 1160, 410, 200, "Generar PDF", ["Incluye datos y equipos", "Devuelve el acta", "para revisión y entrega"], "green"),
        Node("trace", 820, 950, 960, 95, "Historial relacionado", ["Todos los efectos quedan vinculados a la ficha del usuario."], "violet", True),
    ]
    edges = [
        Edge([(540, 327), (720, 327)]),
        Edge([(1200, 327), (1380, 327)]),
        Edge([(1840, 327), (2020, 327)]),
        Edge([(1610, 410), (1610, 490), (440, 490), (440, 615)], "estado", (970, 478), "green"),
        Edge([(1610, 410), (1610, 535), (1280, 535), (1280, 615)], "estado", (1390, 523), "amber"),
        Edge([(1610, 410), (1610, 490), (2120, 490), (2120, 615)], "estado", (1840, 478), "red"),
        Edge([(440, 945), (440, 997), (820, 997)], "historial", (590, 985), "violet"),
        Edge([(1280, 945), (1280, 950)], "historial", (1295, 922), "violet"),
        Edge([(2120, 945), (2120, 997), (1780, 997)], "historial", (1850, 985), "violet"),
        Edge([(510, 1272), (680, 1272)]),
        Edge([(1200, 1272), (1390, 1272)], "NO", (1260, 1260), "red"),
        Edge([(940, 1360), (940, 1430), (2255, 1430), (2255, 1360)], "SÍ", (1580, 1418), "green"),
    ]
    return Diagram(
        "flujo_estados_usuario",
        2600,
        1570,
        "Usuarios — Estados, recursos y acta de entrega",
        "Comportamiento confirmado para ACTIVO, LICENCIA MÉDICA y BAJA",
        groups,
        nodes,
        edges,
        "La licencia médica libera solo la IP; la baja libera IP, equipos y anexo.",
    )


def data_model():
    groups = [
        Group(55, 165, 2570, 495, "Organización y personas", "#EFF5FF"),
        Group(55, 690, 2570, 765, "Activos, conectividad y propietarios", "#F4F8F6"),
        Group(55, 1485, 2570, 660, "Historial funcional", "#F8F5FF"),
        Group(2660, 165, 680, 1980, "Autenticación y auditoría", "#FFF8EC"),
    ]
    nodes = [
        Node("dept", 110, 255, 470, 250, "Departamento", ["PK id", "UQ nombre_normalizado", "activo · timestamps"], "blue"),
        Node("sub", 680, 255, 470, 250, "SubÁrea", ["PK id", "FK departamento (PROTECT)", "UQ departamento + nombre"], "blue"),
        Node("user", 1250, 220, 600, 355, "Usuario", ["PK id", "FK departamento / subárea", "UQ nombre, red y correo", "estado · hostname", "secretos ENC2::"], "blue"),
        Node("profile", 1950, 255, 600, 250, "PerfilGenérico", ["PK id", "FK departamento / subárea", "UQ nombre y usuario", "password ENC2::"], "violet"),
        Node("equipment", 110, 800, 530, 305, "Equipamiento", ["PK id · FK usuario SET_NULL", "tipo · marca · modelo", "UQ serie / hostname / AF", "estado · PIN/clave ENC2::"], "green"),
        Node("extension", 110, 1175, 530, 200, "Anexo", ["PK id · UQ número", "O2O usuario SET_NULL", "estado coherente con dueño"], "green"),
        Node("ip", 850, 800, 520, 270, "IP", ["PK id · UQ dirección", "O2O usuario SET_NULL", "LIBRE o RESERVADA", "proyección compatible"], "green"),
        Node("assignment", 1510, 760, 650, 390, "AsignacionIP", ["PK id · O2O ip CASCADE", "un solo propietario:", "usuario | servidor | pc | otro", "UQ por cada propietario", "check de exclusividad"], "amber"),
        Node("server", 2250, 760, 300, 240, "Servidor", ["PK id", "UQ hostname", "O2O ip PROTECT"], "green", True),
        Node("pc", 2250, 1090, 300, 280, "PCGenérico", ["PK id", "FK depto/subárea", "UQ identificadores", "O2O ip PROTECT"], "green", True),
        Node("huser", 110, 1585, 420, 305, "HistorialUsuario", ["FK usuario SET_NULL", "módulo + objeto", "actor · fecha · acción", "antes / después"], "violet", True),
        Node("hequipment", 580, 1585, 420, 305, "HistorialEquipo", ["FK equipo SET_NULL", "usuario anterior/nuevo", "actor · fecha · acción"], "violet", True),
        Node("hext", 1050, 1585, 420, 305, "HistorialAnexo", ["FK anexo SET_NULL", "usuario anterior/nuevo", "actor · fecha · acción"], "violet", True),
        Node("hip", 1520, 1585, 480, 305, "HistorialAsignacionIP", ["FK IP SET_NULL", "propietario anterior/nuevo", "actor · fecha · acción"], "violet", True),
        Node("hserver", 2050, 1585, 460, 220, "HistorialServidor", ["FK servidor SET_NULL", "actor · fecha · acción"], "violet", True),
        Node("hmore", 2050, 1870, 460, 210, "Otros historiales", ["PC genérico", "Perfil genérico"], "violet", True),
        Node("authuser", 2720, 255, 560, 260, "auth.User + Group", ["Identidad del operador", "Roles y permisos Django", "Contraseña con hash"], "amber"),
        Node("session", 2720, 655, 560, 300, "PortalSession", ["FK auth.User CASCADE", "sid único", "last_activity", "revocación e inactividad"], "amber"),
        Node("token", 2720, 1060, 560, 240, "JWT blacklist", ["Refresh emitidos", "Tokens bloqueados", "Datos transitorios"], "amber"),
        Node("audit", 2720, 1410, 560, 320, "SecurityAuditLog", ["Sin FK deliberadamente", "actor y request_id", "evento, resultado y metadata", "nunca guarda secretos"], "red"),
        Node("migrations", 2720, 1840, 560, 220, "django_migrations", ["Versión del esquema", "Django es la fuente de verdad"], "slate"),
    ]
    edges = [
        Edge([(580, 380), (680, 380)], "1 : N", (600, 365), "blue"),
        Edge([(400, 505), (400, 600), (1450, 600), (1450, 575)], "1 : N", (1030, 588), "blue"),
        Edge([(1150, 380), (1250, 380)], "0..1 : N", (1165, 365), "blue"),
        Edge([(500, 505), (500, 620), (2250, 620), (2250, 505)], "1 : N", (1740, 608), "violet"),
        Edge([(1450, 575), (1450, 680), (375, 680), (375, 800)], "1 : N", (850, 668), "green"),
        Edge([(1250, 500), (760, 500), (760, 1275), (640, 1275)], "0..1 : 1", (675, 1258), "green"),
        Edge([(1550, 575), (1550, 700), (1110, 700), (1110, 800)], "0..1 : 1", (1160, 688), "green"),
        Edge([(1370, 935), (1510, 935)], "1 : 1", (1405, 920), "amber"),
        Edge([(2250, 880), (2160, 880)], "0..1 : 1", (2170, 865), "amber"),
        Edge([(2250, 1230), (2190, 1230), (2190, 1090), (2160, 1090)], "0..1 : 1", (2170, 1215), "amber"),
        Edge([(1350, 575), (1350, 1510), (320, 1510), (320, 1585)], "1 : N", (720, 1498), "violet", True),
        Edge([(375, 1105), (375, 1535), (790, 1535), (790, 1585)], "1 : N", (520, 1523), "violet", True),
        Edge([(375, 1375), (375, 1555), (1260, 1555), (1260, 1585)], "1 : N", (860, 1543), "violet", True),
        Edge([(1110, 1070), (1110, 1565), (1760, 1565), (1760, 1585)], "1 : N", (1350, 1553), "violet", True),
        Edge([(2550, 880), (2600, 880), (2600, 1695), (2510, 1695)], "1 : N", (2530, 1678), "violet", True),
        Edge([(2550, 1230), (2570, 1230), (2570, 1975), (2510, 1975)], "1 : N", (2530, 1958), "violet", True),
        Edge([(3000, 515), (3000, 655)], "1 : N", (3015, 570), "amber"),
        Edge([(3000, 955), (3000, 1060)], "sid/JWT", (3015, 1000), "amber"),
        Edge([(2720, 385), (2630, 385), (2630, 1570), (2720, 1570)], "actor", (2645, 960), "red", True),
    ]
    return Diagram(
        "modelo_datos_er",
        3400,
        2210,
        "Portal Infraestructura TI — Modelo de datos",
        "Entidades principales, cardinalidades, propietarios de IP, historiales y seguridad",
        groups,
        nodes,
        edges,
        "UQ = restricción única · O2O = uno a uno · FK = clave foránea · PROTECT/SET_NULL/CASCADE indican borrado referencial",
    )


def current_actions():
    groups = [
        Group(60, 165, 3480, 350, "Acceso, sesión y autorización", "#EFF5FF"),
        Group(60, 545, 3480, 360, "Acciones habilitadas según el rol", "#FFF8EC"),
        Group(60, 935, 3480, 1080, "Acciones disponibles por módulo", "#F4F8F6"),
        Group(60, 2045, 3480, 430, "Qué ocurre al confirmar una acción", "#F8F5FF"),
    ]
    nodes = [
        Node(
            "access",
            100,
            245,
            720,
            190,
            "1. Iniciar sesión",
            ["Credenciales y protección CSRF", "Se emiten JWT y un sid único", "El refresh queda en cookie HttpOnly"],
            "blue",
            True,
        ),
        Node(
            "session",
            930,
            245,
            720,
            190,
            "2. Mantener la sesión",
            ["Actividad real renueva la vigencia", "5 minutos de inactividad cierran sesión", "Recargar conserva una sesión válida"],
            "violet",
            True,
        ),
        Node(
            "role",
            1760,
            245,
            720,
            190,
            "3. Resolver permisos",
            ["Visualizador", "Operador Infraestructura", "Administrador o superusuario"],
            "amber",
            True,
        ),
        Node(
            "enforce",
            2590,
            245,
            870,
            190,
            "4. Aplicar la regla en backend",
            ["Cada endpoint valida el rol", "La interfaz no reemplaza la autorización", "Las acciones prohibidas responden 403"],
            "red",
            True,
        ),
        Node(
            "viewer",
            100,
            625,
            1000,
            200,
            "Visualizador",
            ["Solo accede a Anexos", "Lista, busca, filtra y pagina", "Puede consultar el historial", "No crea, edita, elimina, exporta ni revela"],
            "blue",
            True,
        ),
        Node(
            "operator",
            1300,
            625,
            1000,
            200,
            "Operador Infraestructura",
            ["Consulta todos los módulos habilitados", "Crea, edita, asigna, libera y exporta", "Consulta fichas e historiales", "No elimina registros ni revela secretos"],
            "green",
            True,
        ),
        Node(
            "admin",
            2500,
            625,
            960,
            200,
            "Administrador / superusuario",
            ["Incluye todas las acciones operativas", "Puede eliminar según las reglas del módulo", "Revela secretos después de reautenticarse", "El revelado queda auditado y vence"],
            "red",
            True,
        ),
        Node(
            "users",
            100,
            1015,
            750,
            430,
            "Usuarios",
            [
                "Seleccionar departamento o área",
                "Buscar, filtrar, paginar y exportar",
                "Agregar, editar y consultar ficha",
                "Elegir segmento y una IP disponible",
                "Asignar equipos y anexo",
                "Ver historial propio y relacionado",
                "Revelar claves Gmail/VPN (admin)",
                "Emitir acta solo si posee equipos",
                "Cambiar estado con advertencia previa",
            ],
            "blue",
            True,
        ),
        Node(
            "equipment",
            970,
            1015,
            750,
            430,
            "Equipos",
            [
                "Acceso directo por tipo de dispositivo",
                "Notebook, celular, tablet y Mac",
                "BAM / Router y periféricos",
                "Buscar, filtrar estado y paginar",
                "Agregar, editar y exportar",
                "Asignar o desasignar usuario",
                "Ver historial de movimientos",
                "Ver IP del usuario en Notebook",
                "Revelar PIN o secreto (admin)",
            ],
            "green",
            True,
        ),
        Node(
            "ips",
            1840,
            1015,
            750,
            430,
            "Gestión de IP",
            [
                "Seleccionar segmento de red",
                "Ver libres y reservadas por segmento",
                "Ordenar por el último octeto numérico",
                "Buscar, filtrar, paginar y exportar",
                "Agregar, editar y consultar historial",
                "Asignar un único propietario",
                "Sincronizar usuario, servidor o PC",
                "Liberar desde el módulo propietario",
                "Eliminar solo una IP libre (admin)",
            ],
            "green",
            True,
        ),
        Node(
            "extensions",
            2710,
            1015,
            750,
            430,
            "Anexos",
            [
                "Listar disponibles y asignados",
                "Buscar, filtrar y paginar",
                "Agregar, editar y exportar",
                "Asignar o liberar un usuario",
                "Consultar historial del anexo",
                "Mantener coherencia de estado y dueño",
                "Eliminar el anexo (admin)",
                "Único módulo visible al Visualizador",
            ],
            "blue",
            True,
        ),
        Node(
            "profiles",
            100,
            1505,
            750,
            430,
            "Perfiles genéricos",
            [
                "Filtrar por departamento o subárea",
                "Buscar, paginar y exportar",
                "Agregar y editar perfil",
                "Activar o desactivar",
                "Consultar historial",
                "Revelar contraseña con reautenticación",
                "Eliminar perfil (admin)",
                "Guardar contraseñas cifradas",
            ],
            "violet",
            True,
        ),
        Node(
            "organization",
            970,
            1505,
            750,
            430,
            "Departamentos y subáreas",
            [
                "Buscar y recorrer tarjetas ordenadas",
                "Agregar y editar departamento",
                "Activar o desactivar departamento",
                "Agregar subárea si el departamento está activo",
                "Editar, activar o desactivar subárea",
                "Conservar relaciones al desactivar",
                "Eliminar sin registros relacionados (admin)",
                "Bloquear borrado con usuarios, perfiles o PCs",
            ],
            "blue",
            True,
        ),
        Node(
            "generic_pc",
            1840,
            1505,
            750,
            430,
            "PCs genéricos",
            [
                "Buscar, filtrar por área y paginar",
                "Agregar, editar y exportar",
                "Relacionar departamento y subárea",
                "Elegir segmento y una IP disponible",
                "Cambiar o liberar la IP sincronizada",
                "Mostrar la IP en el listado",
                "Consultar historial",
                "Revelar contraseña y eliminar (admin)",
            ],
            "green",
            True,
        ),
        Node(
            "servers",
            2710,
            1505,
            750,
            430,
            "Servidores",
            [
                "Buscar, paginar y exportar",
                "Agregar y editar servidor",
                "Elegir solo una IP disponible",
                "Restringir IP al segmento 172.23.1.0/24",
                "Cambiar o liberar la IP",
                "Sincronizar estado en Gestión de IP",
                "Consultar historial",
                "Eliminar servidor (admin)",
            ],
            "green",
            True,
        ),
        Node(
            "validation",
            100,
            2140,
            750,
            230,
            "1. Validación",
            ["Campos, duplicados y relaciones", "Rol y restricciones del módulo", "Confirmación o advertencia cuando aplica"],
            "amber",
            True,
        ),
        Node(
            "sync",
            960,
            2140,
            750,
            230,
            "2. Cambio atómico",
            ["La operación se ejecuta completa", "IP, dueño y estado se sincronizan", "Un fallo revierte todos los cambios"],
            "green",
            True,
        ),
        Node(
            "history",
            1820,
            2140,
            750,
            230,
            "3. Trazabilidad",
            ["Se registra actor, fecha y acción", "Se enlazan los módulos relacionados", "Los eventos sensibles van a auditoría"],
            "violet",
            True,
        ),
        Node(
            "response",
            2680,
            2140,
            780,
            230,
            "4. Resultado en pantalla",
            ["Mensaje de éxito o error explicativo", "Se actualiza el registro afectado", "Las listas reflejan el nuevo estado"],
            "blue",
            True,
        ),
    ]
    edges = [
        Edge([(820, 340), (930, 340)]),
        Edge([(1650, 340), (1760, 340)]),
        Edge([(2480, 340), (2590, 340)]),
        Edge([(2120, 435), (2120, 525), (600, 525), (600, 625)], "lectura", (700, 512), "blue"),
        Edge([(2120, 435), (2120, 565), (1800, 565), (1800, 625)], "operación", (1840, 552), "green"),
        Edge([(2120, 435), (2120, 525), (2980, 525), (2980, 625)], "control total", (2660, 512), "red"),
        Edge([(1800, 2015), (1800, 2085), (475, 2085), (475, 2140)], "confirmar", (1020, 2072), "amber"),
        Edge([(850, 2255), (960, 2255)]),
        Edge([(1710, 2255), (1820, 2255)]),
        Edge([(2570, 2255), (2680, 2255)]),
    ]
    return Diagram(
        "mapa_acciones_actuales",
        3600,
        2550,
        "Portal Infraestructura TI — Mapa de acciones actuales",
        "Qué puede hacer cada rol, qué ofrece cada módulo y qué efectos produce una acción confirmada",
        groups,
        nodes,
        edges,
        "Rojo = acción administrativa o restricción · Verde = operación · Violeta = seguridad o historial · Actualizado: 28-09-2026",
    )


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for diagram in (general_flow(), user_state_flow(), data_model(), current_actions()):
        render_png(diagram)
        render_svg(diagram)
        print(f"Generados: {diagram.filename}.png y {diagram.filename}.svg")


if __name__ == "__main__":
    main()
