"""
build_fase1_componentes.py — Diagrama de COMPONENTES de Fase 1 (end-to-end).

⚠️  SCAFFOLD INICIAL — NO REGENERAR sin re-portar cambios.
    El `fase1-componentes.drawio` fue AJUSTADO A MANO después de generarlo (cajas,
    líneas, posiciones). Si corrés este script, pisás esos ajustes. El `.drawio` es
    la fuente de verdad; este `.py` queda como historia de cómo se armó la base.


5 zonas: Ingesta del árbol → Detección (EMR + JDLC) → Máquina de estados (KEM + state
lambdas + DDB) → Generación del Excel → Validación del Excel → (dispara Fase 2).
Sólo nombres de componente (sin IDs de ticket). Íconos AWS reales (engine aws_drawio);
JDLC con el ícono oficial de Bedrock embebido (assets/bedrock.png).

Uso:  python3 build_fase1_componentes.py   (escribe fase1-componentes.drawio en ../)
"""
import os
from aws_drawio import Diagram

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))

YELLOW = ("#FFF8E1", "#D9A406")
GRAY_SYS = ("#737373", "#555555")
EXT = ("#ECECEC", "#879196")       # caja externa / actor
JSONBG = ("#F0F2F5", "#9AA5B1")
TERM = ("#E5DBFF", "#7048E8")      # terminador → Fase 2


def build() -> Diagram:
    d = Diagram(name="Fase 1 — Componentes", page_w=3180, page_h=1560)

    d.text("title", "Fase 1 — Diagrama de componentes", 60, 22, 2400, 38, size=28, bold=True)
    d.text("sub", "Ingesta del árbol por estación → detección (EMR + JDLC) → máquina de estados "
           "→ generación del Excel → validación del cliente → dispara Fase 2.",
           60, 66, 2900, 24, size=14, color="#5f6368")

    # =====================================================================
    # ZONAS
    # =====================================================================
    d.group("z1", "phase", "1 · INGESTA DEL ÁRBOL", 360, 110, 1080, 610)
    d.group("z2", "phase", "2 · DETECCIÓN — EMR + JDLC", 1480, 110, 900, 610)
    d.group("z3", "phase", "3 · MÁQUINA DE ESTADOS", 360, 800, 960, 620)
    d.group("z4", "phase", "4 · GENERACIÓN DEL EXCEL", 1360, 800, 500, 620)
    d.group("z5", "phase", "5 · VALIDACIÓN DEL EXCEL", 1900, 800, 1200, 620)

    # =====================================================================
    # ACTORES
    # =====================================================================
    d.box("win", "Windows Agent  ·  [Software System]\n\nEscanea documentos de workstations "
          "en la red local del cliente.", 30, 200, 300, 170,
          fill=GRAY_SYS[0], stroke=GRAY_SYS[1], font_color="#FFFFFF", bold=True, font=14,
          valign="top")
    d.box("cloud", "Cloud Agent  ·  [Software System]\n\nEscanea GSuite / OneDrive / SharePoint "
          "y envía los payloads al Classifier.", 30, 470, 300, 170,
          fill=GRAY_SYS[0], stroke=GRAY_SYS[1], font_color="#FFFFFF", bold=True, font=14,
          valign="top")

    # =====================================================================
    # ZONA 1 — INGESTA
    # =====================================================================
    d.node("apitrees", "api_gateway", "/trees", 500, 210, status="deployed")
    d.node("uploader", "lambda", "tree-url-generator", 820, 210, status="deployed")
    d.box("reqjson", "Request\n{ enterprise_id, area_id, station_id,\n  total_lines, fingerprint,\n"
          "  agent_version }", 1120, 140, 300, 110, fill=JSONBG[0], stroke=JSONBG[1],
          font=11, align="left", valign="top")
    d.box("respjson", "Response · pre-signed URL\n{ tree_id, upload_url,\n"
          "  headers: x-amz-meta-* }", 1120, 280, 300, 110, fill=JSONBG[0], stroke=JSONBG[1],
          font=11, align="left", valign="top")
    d.box("note_area", "Agregar el área de donde\nviene el documento (area_id)",
          480, 380, 250, 70, fill=YELLOW[0], stroke=YELLOW[1], font=11)
    d.node("s3comp", "s3", "compressed_trees\n{ent}/{sta}.jsonl.gz", 500, 520, status="deployed")
    d.node("uncomp", "lambda", "tree-uncompressor", 820, 520, status="deployed")
    d.node("s3dec", "s3", "decompressed_trees\n{ent}/{sta}.jsonl", 1120, 520, status="deployed")

    # =====================================================================
    # ZONA 2 — DETECCIÓN
    # =====================================================================
    d.image("jdlc", os.path.join(HERE, "assets", "bedrock.png"),
            "JDLC · detector agentic", 1900, 160)
    d.node("s3search", "s3", "s3_search_engine\n2K-5K keywords", 1900, 350, status="deployed")
    d.node("eb", "eventbridge", "EventBridge\nemr-job-trigger", 1560, 520, status="deployed")
    d.node("emr", "emr", "joyas-priorizer\nEMR Serverless", 1900, 520, status="deployed")
    d.node("crown", "s3", "crown_jewels\ncrown_jewels.json + rollup.json", 2220, 520,
           status="deployed")
    d.box("emrnote", "Matchea keywords (broadcast) contra los\nnombres de archivo → árbol "
          "reducido (solo matches)", 1540, 640, 430, 70, fill=("#FFFFFF", "#879196")[0],
          stroke="#879196", font=11, align="left", valign="top")

    # =====================================================================
    # ZONA 3 — MÁQUINA DE ESTADOS
    # =====================================================================
    d.box("kem", "KEM API\nstations_expected", 400, 900, 210, 80, fill=EXT[0], stroke=EXT[1],
          dashed=True, font=12, bold=True)
    d.node("init", "lambda", "state-enterprise-init", 700, 880, status="rfc")
    d.node("barrier", "lambda", "state-exploration-barrier", 700, 1130, status="rfc")
    d.node("ddb", "dynamodb", "classifier-cycles-state\n+ Stream", 1060, 980, status="deployed",
           w=120, h=120)

    # =====================================================================
    # ZONA 4 — GENERACIÓN DEL EXCEL
    # =====================================================================
    d.node("consol", "lambda", "crown-report-consolidator", 1450, 900, status="rfc")
    d.node("pending", "s3", "crown-reports-pending\nassessment.xlsx", 1450, 1150, status="rfc")

    # =====================================================================
    # ZONA 5 — VALIDACIÓN DEL EXCEL
    # =====================================================================
    d.box("cliente", "Cliente\nvalida el Excel (offline)", 1950, 880, 220, 90,
          fill=GRAY_SYS[0], stroke=GRAY_SYS[1], font_color="#FFFFFF", bold=True, font=13)
    d.node("validated", "s3", "crown-reports-validated\nassessment.xlsx", 2260, 900, status="rfc")
    d.node("ingest", "lambda", "crown-excel-ingest-confirm", 2580, 900, status="rfc")
    d.node("manifest", "s3", "validated_crown_jewels\nmanifest.json + station files", 2580, 1150,
           status="rfc")
    d.box("fase2", "→ Fase 2 · GSE", 2880, 1170, 180, 70, fill=TERM[0], stroke=TERM[1],
          dashed=True, font=13, bold=True)

    # =====================================================================
    # NOTAS — asociación fina a su componente
    # =====================================================================
    d.edge("reqjson", "apitrees", "", "assoc", exit_xy=(0, 0.5), entry_xy=(1, 0.3))
    d.edge("respjson", "uploader", "", "assoc", exit_xy=(0, 0.7), entry_xy=(1, 0.6))
    d.edge("note_area", "uploader", "", "assoc", exit_xy=(0.5, 0), entry_xy=(0.5, 1))
    d.edge("emrnote", "emr", "", "assoc", exit_xy=(0.5, 0), entry_xy=(0.5, 1))

    # =====================================================================
    # EDGES — síncronos
    # =====================================================================
    d.edge("win", "apitrees", "Requests pre-signed URL", "sync",
           exit_xy=(1, 0.4), entry_xy=(0, 0.5))
    d.edge("apitrees", "uploader", "", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("uploader", "win", "pre-signed URL (resp)", "async",
           exit_xy=(0.5, 0), entry_xy=(0.5, 0), points=[(868, 150), (180, 150)])
    d.edge("win", "s3comp", "PUT a S3 (signed URL)", "sync",
           exit_xy=(0.5, 1), entry_xy=(0, 0.5), points=[(180, 568), (500, 568)])
    d.edge("uncomp", "s3dec", "", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("cloud", "s3dec", "PUT directo (IAM) · sin gzip", "sync",
           exit_xy=(1, 0.5), entry_xy=(0.5, 1), points=[(1168, 690)])
    d.edge("eb", "emr", "start job", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("jdlc", "s3search", "keywords.jsonl", "sync", exit_xy=(0.5, 1), entry_xy=(0.5, 0))
    d.edge("s3search", "emr", "loads (broadcast)", "sync", exit_xy=(0.5, 1), entry_xy=(0.5, 0))
    d.edge("emr", "crown", "árbol reducido", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    # estado
    d.edge("kem", "init", "stations_expected", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("init", "ddb", "alta ENTERPRISE+CYCLE (initialized)", "sync",
           exit_xy=(1, 0.5), entry_xy=(0, 0.2))
    d.edge("barrier", "ddb", "barrier → CYCLE ready", "sync",
           exit_xy=(1, 0.5), entry_xy=(0, 0.85))
    # generación Excel
    d.edge("ddb", "consol", "CYCLE ready (stream)", "sync", exit_xy=(1, 0.4), entry_xy=(0, 0.5))
    d.edge("consol", "pending", "assessment.xlsx", "sync", exit_xy=(0.5, 1), entry_xy=(0.5, 0))
    d.edge("consol", "ddb", "awaiting_validation", "sync",
           exit_xy=(0, 0.7), entry_xy=(1, 0.6))
    # validación
    d.edge("pending", "cliente", "descarga Excel", "sync",
           exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("cliente", "validated", "sube Excel validado", "sync",
           exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("ingest", "manifest", "manifest.json", "sync", exit_xy=(0.5, 1), entry_xy=(0.5, 0))
    d.edge("manifest", "fase2", "dispara", "sync", exit_xy=(1, 0.5), entry_xy=(0, 0.5))

    # =====================================================================
    # EDGES — asíncronos / cross-band (rutados por canales vacíos)
    # =====================================================================
    d.edge("s3comp", "uncomp", "S3 PutObject event", "async",
           exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    d.edge("s3dec", "eb", "trigger (EB · .jsonl)", "async",
           exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    # crown_jewels → barrier (canal superior y=760)
    d.edge("crown", "barrier", "rollup.json (fin de estación)", "async",
           exit_xy=(0.5, 1), entry_xy=(0.5, 0), points=[(2268, 760), (748, 760)])
    # crown_jewels → consolidator (lee rollups, canal y=742)
    d.edge("crown", "consol", "lee rollups", "async",
           exit_xy=(0.5, 1), entry_xy=(0.5, 0), points=[(2268, 742), (1498, 742)])
    # validated → ingest (S3 event)
    d.edge("validated", "ingest", "S3 event", "async", exit_xy=(1, 0.5), entry_xy=(0, 0.5))
    # ingest → ddb (confirmed) por canal inferior y=1360
    d.edge("ingest", "ddb", "confirmed", "async",
           exit_xy=(0.5, 1), entry_xy=(0.5, 1), points=[(2628, 1360), (1120, 1360)])

    # =====================================================================
    # Leyenda
    # =====================================================================
    d.legend(2640, 360)
    d.edge_legend(360, 1470)
    return d


if __name__ == "__main__":
    out = os.path.join(OUT, "fase1-componentes.drawio")
    build().write(out)
    print(f"OK: {out}")
