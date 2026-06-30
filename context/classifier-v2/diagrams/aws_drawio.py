"""
aws_drawio.py — Engine genérico para emitir diagramas draw.io con íconos AWS reales.

Por qué existe: los .drawio escritos a mano salían como cajas de colores genéricas
(0 íconos AWS, 120 rectángulos). Este engine usa la librería oficial `mxgraph.aws4`
de draw.io (los mismos shapes que salen al arrastrar un servicio desde el panel AWS),
con colores por categoría, contenedores de grupo (AWS Cloud / Region / VPC) y un badge
de estado por nodo (deployed / WIP / blocked / RFC).

No es maquinaria atada al Classifier: el catálogo y las convenciones son genéricas.
El spec concreto de un producto vive en su propio build (ej. build_classifier.py).

Referencia de shapes: https://www.drawio.com/doc/faq/aws-icons
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Colores oficiales por categoría AWS (paleta 2023+). El color va en fillColor
# del resourceIcon: es lo que distingue "Compute naranja" de "Database morado".
# ---------------------------------------------------------------------------
CAT = {
    "compute": "#ED7100",
    "containers": "#ED7100",
    "storage": "#7AA116",
    "database": "#C925D1",
    "networking": "#8C4FFF",
    "app_integration": "#E7157B",
    "security": "#DD344C",
    "analytics": "#8C4FFF",
    "ml": "#01A88D",
    "management": "#E7157B",
    "frontend": "#C925D1",
}

# Catálogo: clave lógica -> (resIcon de aws4, color de categoría).
# Ampliá esto cuando necesites un servicio nuevo: el resIcon es el nombre
# exacto del shape en mxgraph.aws4 (mismo string que usa draw.io internamente).
ICONS = {
    "lambda":         ("mxgraph.aws4.lambda", CAT["compute"]),
    "emr":            ("mxgraph.aws4.emr", CAT["analytics"]),
    "s3":             ("mxgraph.aws4.s3", CAT["storage"]),
    "dynamodb":       ("mxgraph.aws4.dynamodb", CAT["database"]),
    "api_gateway":    ("mxgraph.aws4.api_gateway", CAT["app_integration"]),
    "sqs":            ("mxgraph.aws4.simple_queue_service_sqs", CAT["app_integration"]),
    "eventbridge":    ("mxgraph.aws4.eventbridge", CAT["app_integration"]),
    "appsync":        ("mxgraph.aws4.appsync", CAT["app_integration"]),
    "opensearch":     ("mxgraph.aws4.opensearch_service", CAT["analytics"]),
    "secrets":        ("mxgraph.aws4.secrets_manager", CAT["security"]),
    "cognito":        ("mxgraph.aws4.cognito", CAT["security"]),
    "bedrock":        ("mxgraph.aws4.bedrock", CAT["ml"]),
    "step_functions": ("mxgraph.aws4.step_functions", CAT["app_integration"]),
    "sns":            ("mxgraph.aws4.simple_notification_service_sns", CAT["app_integration"]),
}

# Grupos / contenedores AWS. kind -> (grIcon | None, stroke, fill, dashed)
GROUPS = {
    "aws_cloud": ("mxgraph.aws4.group_aws_cloud_alt", "#232F3E", "none", 0),
    "region":    ("mxgraph.aws4.group_region", "#00A4A6", "none", 1),
    "vpc":       ("mxgraph.aws4.group_vpc", "#8C4FFF", "none", 0),
    # "phase" no es un constructo AWS: es un frame lógico para agrupar por fase.
    "phase":     (None, "#5A6B86", "#F2F5FA", 1),
}

# Badge de estado (elipse arriba-derecha del ícono). Mantiene el ícono con su
# color de categoría y comunica el estado por separado, sin ensuciar el shape.
STATUS = {
    "deployed": "#1D8102",  # verde
    "wip":      "#D9A406",  # amarillo
    "blocked":  "#C7253E",  # rojo
    "rfc":      "#1976D2",  # azul
}

# Actores externos / cajas negras (no son servicios AWS).
ACTOR_ICONS = {
    "user":   "mxgraph.aws4.user",
    "users":  "mxgraph.aws4.users",
    "client": "mxgraph.aws4.client",
    "server": "mxgraph.aws4.traditional_server",
    "mobile": "mxgraph.aws4.mobile_client",
}

ICON_W = 96
ICON_H = 96


def esc(s: str) -> str:
    """Escapa para atributos XML; \\n -> salto de línea de draw.io."""
    s = (s.replace("&", "&amp;").replace("<", "&lt;")
          .replace(">", "&gt;").replace('"', "&quot;"))
    return s.replace("\n", "&#10;")


@dataclass
class Diagram:
    name: str
    title: str = ""
    subtitle: str = ""
    page_w: int = 1600
    page_h: int = 1200
    cells: list[str] = field(default_factory=list)

    # -- nodos ---------------------------------------------------------------
    def node(self, nid: str, icon: str, label: str, x: int, y: int,
             status: Optional[str] = None, parent: str = "1",
             w: int = ICON_W, h: int = ICON_H, font: int = 15) -> str:
        if icon not in ICONS:
            raise KeyError(f"icono AWS desconocido: {icon!r} (agregalo a ICONS)")
        res, color = ICONS[icon]
        style = (
            "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
            f"fillColor={color};strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;"
            f"verticalAlign=top;align=center;html=1;fontSize={font};fontStyle=0;aspect=fixed;"
            f"shape=mxgraph.aws4.resourceIcon;resIcon={res};labelPosition=center;"
        )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        if status:
            c = STATUS[status]
            self.cells.append(
                f'<mxCell id="{nid}-st" value="" '
                f'style="ellipse;fillColor={c};strokeColor=#ffffff;strokeWidth=2;" '
                f'vertex="1" parent="{nid}">'
                f'<mxGeometry x="{w - 18}" y="-6" width="18" height="18" as="geometry"/></mxCell>'
            )
        return nid

    def group(self, nid: str, kind: str, label: str, x: int, y: int,
              w: int, h: int, parent: str = "1") -> str:
        gr, stroke, fill, dashed = GROUPS[kind]
        if gr:  # contenedor AWS oficial
            style = (
                "sketch=0;outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;"
                "fontSize=13;fontStyle=0;container=1;pointerEvents=0;collapsible=0;"
                "recursiveResize=0;shape=mxgraph.aws4.group;"
                f"grIcon={gr};strokeColor={stroke};fillColor={fill};verticalAlign=top;"
                f"align=left;spacingLeft=38;fontColor={stroke};dashed={dashed};"
            )
        else:  # frame lógico (fase)
            style = (
                "rounded=1;arcSize=3;whiteSpace=wrap;html=1;container=1;collapsible=0;"
                f"fillColor={fill};strokeColor={stroke};dashed={dashed};dashPattern=8 6;"
                "verticalAlign=top;align=left;spacingLeft=14;spacingTop=8;fontSize=16;"
                f"fontStyle=1;fontColor={stroke};"
            )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return nid

    def actor(self, nid: str, label: str, x: int, y: int, kind: str = "user",
              parent: str = "1", w: int = ICON_W, h: int = ICON_H) -> str:
        shape = ACTOR_ICONS[kind]
        style = (
            "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
            "fillColor=#232F3E;strokeColor=none;dashed=0;verticalLabelPosition=bottom;"
            "verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;"
            f"shape={shape};"
        )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return nid

    def image(self, nid: str, png_path: str, label: str, x: int, y: int,
              w: int = ICON_W, h: int = ICON_H, parent: str = "1", font: int = 13) -> str:
        """Embebe un PNG real como ícono (data:image/png,<b64> — formato que draw.io
        sí renderiza; ver estilo-base §1.1c). Para servicios sin resIcon aws4 confiable."""
        with open(png_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        uri = f"data:image/png,{b64}"  # coma, SIN ;base64
        style = (
            "shape=image;verticalLabelPosition=bottom;verticalAlign=top;aspect=fixed;"
            f"imageAspect=0;image={uri};html=1;fontSize={font};fontStyle=0;fontColor=#232F3E;"
        )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return nid

    def box(self, nid: str, label: str, x: int, y: int, w: int, h: int,
            fill: str = "#FFFFFF", stroke: str = "#879196", parent: str = "1",
            dashed: bool = False, bold: bool = False, font: int = 11,
            align: str = "center", valign: str = "middle",
            font_color: str = "#232F3E") -> str:
        style = (
            f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};fontColor={font_color};fontSize={font};"
            f"fontStyle={1 if bold else 0};align={align};verticalAlign={valign};"
            f"dashed={1 if dashed else 0};{'dashPattern=6 6;' if dashed else ''}"
        )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return nid

    def text(self, nid: str, text: str, x: int, y: int, w: int, h: int,
             size: int = 12, bold: bool = False, color: str = "#232F3E",
             align: str = "center", parent: str = "1") -> str:
        style = (
            f"text;html=1;strokeColor=none;fillColor=none;align={align};"
            f"verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize={size};"
            f"fontStyle={1 if bold else 0};fontColor={color};"
        )
        self.cells.append(
            f'<mxCell id="{nid}" value="{esc(text)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return nid

    # -- edges ---------------------------------------------------------------
    def edge(self, src: str, tgt: str, label: str = "", kind: str = "sync",
             parent: str = "1", exit_xy: Optional[tuple] = None,
             entry_xy: Optional[tuple] = None, points: Optional[list] = None,
             font: int = 13) -> str:
        if kind == "assoc":  # asociación nota↔componente (fina, gris, sin flechas)
            base = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
                    "strokeColor=#9AA5B1;strokeWidth=1;dashed=1;dashPattern=2 3;"
                    f"endArrow=none;startArrow=none;fontSize={font};fontColor=#6B7480;"
                    "labelBackgroundColor=#FFFFFF;")
        elif kind == "async":  # eventos / DDB Stream / S3 PutObject
            base = ("edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=6;"
                    "strokeColor=#E7157B;strokeWidth=2;dashed=1;dashPattern=6 4;"
                    f"endArrow=open;endFill=0;html=1;fontSize={font};fontColor=#A30D5B;"
                    "labelBackgroundColor=#FFFFFF;")
        else:  # invocación síncrona / directa
            base = ("edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=6;"
                    "strokeColor=#545B64;strokeWidth=2;endArrow=block;endFill=1;"
                    f"html=1;fontSize={font};fontColor=#3B4148;"
                    "labelBackgroundColor=#FFFFFF;")
        if exit_xy:
            base += f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0;"
        if entry_xy:
            base += f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0;"
        pts = ""
        if points:
            inner = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points)
            pts = f'<Array as="points">{inner}</Array>'
        eid = f"e-{src}-{tgt}-{len(self.cells)}"
        self.cells.append(
            f'<mxCell id="{eid}" value="{esc(label)}" style="{base}" edge="1" '
            f'parent="{parent}" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return eid

    # -- leyenda reutilizable ------------------------------------------------
    def legend(self, x: int, y: int, parent: str = "1") -> None:
        self.box("legend", "LEYENDA — estado del componente", x, y, 250, 156,
                 fill="#FFFFFF", stroke="#879196", bold=True, font=11,
                 align="left", valign="top")
        items = [
            ("deployed", "Deployed (prod)"),
            ("wip", "WIP / en sprint"),
            ("blocked", "BLOCKED (DevOps)"),
            ("rfc", "RFC (nuevo)"),
        ]
        for i, (st, lbl) in enumerate(items):
            cy = 30 + i * 28
            self.cells.append(
                f'<mxCell id="leg-dot-{st}" value="" '
                f'style="ellipse;fillColor={STATUS[st]};strokeColor=#ffffff;strokeWidth=2;" '
                f'vertex="1" parent="legend">'
                f'<mxGeometry x="14" y="{cy}" width="16" height="16" as="geometry"/></mxCell>'
            )
            self.cells.append(
                f'<mxCell id="leg-lbl-{st}" value="{esc(lbl)}" '
                f'style="text;html=1;align=left;verticalAlign=middle;fontSize=11;strokeColor=none;fillColor=none;" '
                f'vertex="1" parent="legend">'
                f'<mxGeometry x="40" y="{cy - 4}" width="200" height="24" as="geometry"/></mxCell>'
            )

    def edge_legend(self, x: int, y: int) -> None:
        self.text("elx", "——— síncrono / invocación directa      "
                  "- - - evento async (EventBridge · DDB Stream · S3 PutObject)",
                  x, y, 640, 20, size=10, color="#5f6368", align="left")

    # -- ensamblado ----------------------------------------------------------
    def xml(self) -> str:
        body = "\n        ".join(self.cells)
        return (
            f'<mxfile host="app.diagrams.net" agent="classifier-specs/diagram-aws" type="device">\n'
            f'  <diagram name="{esc(self.name)}" id="{esc(self.name)}">\n'
            f'    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{self.page_w}" pageHeight="{self.page_h}" math="0" shadow="0">\n'
            f'      <root>\n'
            f'        <mxCell id="0"/>\n'
            f'        <mxCell id="1" parent="0"/>\n'
            f'        {body}\n'
            f'      </root>\n'
            f'    </mxGraphModel>\n'
            f'  </diagram>\n'
            f'</mxfile>\n'
        )

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.xml())
