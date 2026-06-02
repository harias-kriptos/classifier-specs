"""
build_classifier.py — Spec declarativo de los diagramas del Classifier Backend v2.

Define los componentes reales (4 actores, ~30 servicios AWS, 3 cajas negras de IA,
la DDB compartida KT-17009) y su flujo en 3 fases, y emite los .drawio con íconos
AWS reales vía aws_drawio.Diagram.

Genera:
  - architecture.drawio          (detallada: flujo completo de las 3 fases)
  - architecture-complete.drawio (detallada + notas de estados / publish-first / repos)
  - architecture-global.drawio   (C4 numerada: walkthrough 1..11 alrededor del state machine)

Uso:  python3 build_classifier.py        (escribe en ../  junto a los demás contextos)
"""
import os
from aws_drawio import Diagram, STATUS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))  # context/classifier-v2/

# Grilla -------------------------------------------------------------------
def C(i: int) -> int:      # columna -> x
    return 300 + i * 320

# Filas (y del ícono)
RK = 268    # keyword cluster (Bedrock)
R0 = 438    # Fase 1 scan
RV1 = 758   # Fase 1 validación, fila 1
RV2 = 948   # Fase 1 validación, fila 2
RF1 = 1248  # Fase 2, fila 1 (colección)
RF2 = 1438  # Fase 2, fila 2 (request-complete)
RF3 = 1628  # Fase 2, fila 3 (state pipes)

DDB_X, DDB_Y = 2880, 940


def build_detailed(notes: bool) -> Diagram:
    d = Diagram(
        name="Classifier Backend v2 — Arquitectura detallada",
        page_w=3700, page_h=1980,
    )
    d.text("title", "Classifier Backend v2 — Arquitectura detallada", 200, 24, 3300, 30,
           size=22, bold=True)
    d.text("sub", "DDB compartida (KT-17009) en el centro · Fase 1 scan+match → validación "
           "humana → Fase 2 GSE sample collection · IA externa como caja negra",
           200, 56, 3300, 22, size=12, color="#5f6368")

    # --- contenedores (van primero: quedan al fondo) ---------------------
    d.group("cloud", "aws_cloud", "AWS Cloud", 200, 150, 2950, 1700)
    d.group("f1scan", "phase", "FASE 1 — Scan + Match", 240, 200, 2560, 410)
    d.group("f1val", "phase", "FASE 1 — Validación humana", 240, 660, 2560, 430)
    d.group("f2", "phase", "FASE 2 — GSE Sample Collection", 240, 1150, 2560, 640)
    d.group("ia", "phase", "Equipo IA (cajas negras · contrato con backend)",
            3210, 280, 410, 900)

    # --- actores externos (izquierda, fuera del cloud) -------------------
    d.actor("win", "Windows Agent", 40, 300, "server")
    d.actor("cloudag", "Cloud Agent", 40, 480, "server")
    d.actor("web", "Plataforma Web\n(cliente final)", 40, 700, "user")
    d.box("kem", "KEM API\n(stations_expected)", 30, 880, 130, 60, fill="#ECECEC",
          stroke="#879196", dashed=True)

    # --- Fase 1: keyword generation (manual) -----------------------------
    d.node("bedrock", "bedrock", "Bedrock\nkeyword gen", C(4), RK, status="deployed")
    d.node("s3kw", "s3", "S3 keywords\n2K-5K patrones", C(5), RK, status="deployed")

    # --- Fase 1: scan + match --------------------------------------------
    d.node("apinit", "api_gateway", "API GW\nPOST /v2/tree/init", C(0), R0, status="deployed")
    d.node("kt16612", "lambda", "KT-16612\ntree-url-generator", C(1), R0, status="deployed")
    d.node("s3comp", "s3", "S3\ncompressed_trees", C(2), R0, status="deployed")
    d.node("kt16613", "lambda", "KT-16613\ntree-uncompressor", C(3), R0, status="blocked")
    d.node("s3dec", "s3", "S3\ndecompressed_trees", C(4), R0, status="rfc")
    d.node("kt16614", "lambda", "KT-16614\nemr-job-trigger", C(5), R0, status="blocked")
    d.node("kt16616", "emr", "KT-16616 joyas-priorizer\nEMR Serverless · Aho-Corasick", C(6), R0, status="wip")
    d.node("s3crown", "s3", "S3 crown_jewels\n(candidatos)", C(7), R0, status="rfc")

    # --- Fase 1: validación humana ---------------------------------------
    d.node("sqsidx", "sqs", "SQS\nindexer-queue + DLQ", C(0), RV1, status="rfc")
    d.node("kt17024", "lambda", "KT-17024\ncrown-candidates-indexer", C(1), RV1, status="rfc")
    d.node("opensearch", "opensearch", "OpenSearch\ncrown_jewel_candidates", C(2), RV1, status="rfc")
    d.node("appsync", "appsync", "AppSync (GraphQL)\nCognito auth", C(4), RV1, status="rfc")
    d.node("kt17026", "lambda", "KT-17026\ncrown-validation-handler", C(5), RV1, status="rfc")
    d.node("secrets", "secrets", "Secrets Mgr\nkem-api-key", C(0), RV2, status="rfc")
    d.node("ebbar", "eventbridge", "EB Pipe · barrier\nSTATION#+scan_status", C(2), RV2, status="rfc")
    d.node("kt17025", "lambda", "KT-17025\ncrown-enterprise-barrier", C(3), RV2, status="rfc")
    d.node("apiconf", "api_gateway", "API GW\nPOST /validation/confirm", C(4), RV2, status="rfc")
    d.node("kt17027", "lambda", "KT-17027\ncrown-validation-confirm", C(5), RV2, status="rfc")
    d.node("s3val", "s3", "S3 validated\nmanifest.json", C(6), RV2, status="rfc")
    d.node("sqsfifo", "sqs", "SQS FIFO\ngse-validated-cycle", C(7), RV2, status="rfc")

    # --- Fase 2: GSE sample collection -----------------------------------
    d.node("kt17028", "lambda", "KT-17028\ngse-cycle-init", C(0), RF1, status="rfc")
    d.node("s3raw", "s3", "S3 gse-raw\n(samples crudos)", C(1), RF1, status="rfc")
    d.node("sqsrec", "sqs", "SQS\nreception-queue + DLQ", C(2), RF1, status="rfc")
    d.node("kt17029", "lambda", "KT-17029\ngse-sample-reception", C(3), RF1, status="rfc")
    d.node("s3anon", "s3", "S3 gse-anonymized", C(4), RF1, status="rfc")
    d.node("sqsanon", "sqs", "SQS\nanonymizer-queue + DLQ", C(5), RF1, status="rfc")
    d.node("kt17030", "lambda", "KT-17030\ngse-sample-anonymizer", C(6), RF1, status="rfc")
    d.node("apireq", "api_gateway", "API GW\nPOST /gse/request-complete", C(0), RF2, status="rfc")
    d.node("kt17031", "lambda", "KT-17031\ngse-request-complete", C(1), RF2, status="rfc")
    d.node("ebstation", "eventbridge", "EB Pipe · station\nSTATION#+sampling_status", C(2), RF3, status="rfc")
    d.node("kt17032", "lambda", "KT-17032\ngse-station-status", C(3), RF3, status="rfc")
    d.node("ebcycle", "eventbridge", "EB Pipe · cycle\nCYCLE#+phase2_collecting", C(4), RF3, status="rfc")
    d.node("kt17033", "lambda", "KT-17033\ngse-enterprise-status", C(5), RF3, status="rfc")

    # --- DDB compartida (centro) -----------------------------------------
    d.node("ddb", "dynamodb", "DDB · KT-17009\nclassifier-cycles-state\nStream + TTL 90d",
           DDB_X, DDB_Y, status="wip", w=110, h=110)

    # --- cajas negras IA --------------------------------------------------
    d.box("signal", "Signal Handler\n(IA — canal TBD)", 3250, 360, 330, 60, fill="#ECECEC", stroke="#879196", dashed=True)
    d.box("anon", "Anonymizer\n(IA caja negra)", 3250, 560, 330, 60, fill="#ECECEC", stroke="#879196", dashed=True)
    d.box("llmq", "LLM Process Queue\n(IA — canal TBD)", 3250, 760, 330, 60, fill="#ECECEC", stroke="#879196", dashed=True)

    # --- edges síncronos --------------------------------------------------
    sync = [
        ("win", "apinit", ""), ("apinit", "kt16612", ""), ("kt16612", "s3comp", "PUT"),
        ("cloudag", "s3dec", "directo"), ("kt16613", "s3dec", ""),
        ("kt16614", "kt16616", "start job"),
        ("bedrock", "s3kw", ""), ("s3kw", "kt16616", "read"),
        ("kt16616", "s3crown", ""),
        ("kt17024", "opensearch", "bulk index"), ("kt17024", "ddb", "create CYCLE/STATION"),
        ("kem", "kt17024", "stations"), ("kt17024", "secrets", "read"),
        ("web", "appsync", ""), ("appsync", "kt17026", "resolver"),
        ("kt17026", "ddb", ""), ("appsync", "opensearch", "queries directas"),
        ("kt17025", "ddb", "barrier write"),
        ("web", "apiconf", ""), ("apiconf", "kt17027", ""),
        ("kt17027", "s3val", "manifest"), ("kt17027", "opensearch", "scroll"), ("kt17027", "ddb", ""),
        ("kt17028", "ddb", "phase2_collecting"), ("kt17028", "signal", "notify"),
        ("anon", "s3anon", "writes"),
        ("kt17029", "ddb", "ADD samples_received"), ("kt17029", "anon", "notify IA"),
        ("kt17030", "ddb", "ADD samples_anonymized"),
        ("cloudag", "apireq", "request-complete"), ("apireq", "kt17031", ""),
        ("kt17031", "ddb", "TransactWriteItems"),
        ("kt17032", "ddb", "close STATION"),
        ("kt17033", "ddb", "TTL +90d cascade"), ("kt17033", "llmq", "publish-first"),
    ]
    for s, t, lbl in sync:
        d.edge(s, t, lbl, "sync")

    # --- edges asíncronos (eventos / streams) ----------------------------
    asyncs = [
        ("s3comp", "kt16613", "EB .jsonl.gz"), ("s3dec", "kt16614", "EB .jsonl"),
        ("s3crown", "sqsidx", "EB .jsonl"), ("sqsidx", "kt17024", ""),
        ("ddb", "ebbar", "Stream"), ("ebbar", "kt17025", ""),
        ("s3val", "sqsfifo", "EB manifest"), ("sqsfifo", "kt17028", ""),
        ("s3raw", "sqsrec", "EB .json"), ("sqsrec", "kt17029", ""),
        ("s3anon", "sqsanon", "EB .json"), ("sqsanon", "kt17030", ""),
        ("ddb", "ebstation", "Stream"), ("ebstation", "kt17032", ""),
        ("ddb", "ebcycle", "Stream"), ("ebcycle", "kt17033", ""),
        ("signal", "s3raw", "via agents"),
    ]
    for s, t, lbl in asyncs:
        d.edge(s, t, lbl, "async")

    # --- leyenda + notas --------------------------------------------------
    d.legend(2870, 1500)
    d.edge_legend(240, 1860)

    if notes:
        d.box("n-estados", "Estados CYCLE: scanning → stations_complete → confirmed → "
              "phase2_collecting → complete  (phase2_skipped si 0 approved)",
              240, 122, 1500, 24, fill="#FFF8E1", stroke="#D9A406", font=10, align="left")
        d.box("n-pub", "Publish-first (KT-17033): 1) publica al LLM  2) si OK → "
              "status=complete + TTL +90d cascade  3) si falla → SQS retry → DLQ  ·  "
              "Contrato: LLM idempotente por cycle_id",
              1760, 122, 1390, 24, fill="#E3F2FD", stroke="#1976D2", font=10, align="left")
        d.box("n-repos", "Repos: s3-tree-uploader, tree-uncompressor, emr-job-trigger, "
              "joyas-priorizer  ·  KT-16613/14 BLOCKED por KT-16726",
              2870, 1672, 760, 60, fill="#FFEBEE", stroke="#C7253E", font=10, align="left")

    return d


def build_global() -> Diagram:
    """C4-style: walkthrough numerado 1..11 alrededor del state machine compartido."""
    d = Diagram(name="Classifier Backend v2 — Architecture Global", page_w=3200, page_h=1700)
    d.text("title", "Classifier Backend v2 — Architecture Global", 60, 24, 3080, 30, size=22, bold=True)
    d.text("sub", "Las 3 fases convergen en el State Machine compartido (DynamoDB classifier-cycles-state)",
           60, 56, 3080, 22, size=12, color="#5f6368")

    # Actores
    d.group("actors", "phase", "1 · EXTERNAL ACTORS", 40, 110, 560, 520)
    d.actor("win", "Windows Agent", 90, 180, "server")
    d.actor("cloudag", "Cloud Agent", 330, 180, "server")
    d.actor("web", "Client UI (Web)\nhuman-in-the-loop", 90, 380, "user")
    d.box("kem", "KEM API\nstations_expected", 320, 400, 220, 60, fill="#ECECEC", stroke="#879196", dashed=True)

    # Fase 1 scan (numerados 1-6)
    d.group("p1", "phase", "2 · FASE 1 — Scan & Match", 660, 110, 1660, 250)
    d.node("g1", "lambda", "1 · tree-url-generator", 700, 190, status="deployed")
    d.node("g2", "s3", "2 · compressed_trees", 940, 190, status="deployed")
    d.node("g3", "lambda", "3 · tree-uncompressor", 1180, 190, status="blocked")
    d.node("g4", "lambda", "4 · emr-job-trigger", 1420, 190, status="blocked")
    d.node("gemr", "emr", "joyas-priorizer\nEMR Serverless", 1660, 190, status="wip")
    d.node("g5", "lambda", "5 · candidates-indexer", 1900, 190, status="rfc")
    d.node("gos", "opensearch", "OpenSearch", 2140, 190, status="rfc")

    # Fase 1 validación
    d.group("p2", "phase", "3 · FASE 1 — Validación humana", 660, 400, 1660, 210)
    d.node("g6", "lambda", "6 · enterprise-barrier", 700, 470, status="rfc")
    d.node("v1", "appsync", "validation-handler\n(AppSync)", 1060, 470, status="rfc")
    d.node("v2", "lambda", "validation-confirm", 1420, 470, status="rfc")
    d.node("vman", "s3", "validated\nmanifest.json", 1780, 470, status="rfc")

    # State machine (centro)
    d.group("sm", "phase", "★ STATE MACHINE ★ · single source of truth · exactly-once", 660, 660, 1660, 300)
    d.node("ddb", "dynamodb", "classifier-cycles-state\nPK=enterprise_id\nSK=CYCLE#/STATION#/REQUEST#",
           1300, 730, status="wip", w=120, h=120)
    d.node("ebr", "eventbridge", "EventBridge Pipes\nfilter por SK/atributo", 1700, 745, status="rfc")
    d.box("smnote", "CYCLE: scanning → stations_complete → confirmed → phase2_collecting → complete\n"
          "DDB Stream at-least-once → conditional writes para exactly-once\n"
          "TTL 90d cascade al cerrar el CYCLE",
          740, 745, 460, 110, fill="#FFFFFF", stroke="#879196", font=10, align="left", valign="top")

    # Fase 2
    d.group("p3", "phase", "4 · FASE 2 — Priority Sample Collection (GSE)", 660, 1010, 1660, 260)
    d.node("f7", "lambda", "7 · gse-cycle-init", 700, 1090, status="rfc")
    d.node("f8", "s3", "8 · gse-raw", 940, 1090, status="rfc")
    d.node("frq", "sqs", "reception-queue", 1180, 1090, status="rfc")
    d.node("f9", "lambda", "9 · reception-notifier", 1420, 1090, status="rfc")
    d.node("fanon", "s3", "gse-anonymized", 1660, 1090, status="rfc")
    d.node("f10", "lambda", "10 · station-status", 1900, 1090, status="rfc")
    d.node("f11", "lambda", "11 · enterprise-status", 2140, 1090, status="rfc")

    # External systems (black boxes)
    d.group("ext", "phase", "5 · EXTERNAL SYSTEMS (black boxes)", 2380, 110, 760, 1160)
    d.box("signal", "Signal Handler\n[External] push cycle a agents", 2410, 200, 700, 64, fill="#ECECEC", stroke="#879196", dashed=True)
    d.node("bedrock", "bedrock", "Bedrock\nkeyword gen", 2700, 380, status="deployed")
    d.box("anon", "Anonymizer\n[External] remove PII\ngse-raw → gse-anonymized", 2410, 560, 700, 70, fill="#ECECEC", stroke="#879196", dashed=True)
    d.box("llmq", "LLM Process Queue\n[External] consume cycle final", 2410, 720, 700, 64, fill="#ECECEC", stroke="#879196", dashed=True)

    # edges (flujo principal)
    sync = [
        ("win", "g1", ""), ("g1", "g2", ""), ("g3", "g2", ""), ("cloudag", "g2", "directo"),
        ("g4", "gemr", ""), ("gemr", "g5", ""), ("g5", "gos", ""), ("g5", "ddb", "create CYCLE"),
        ("g6", "ddb", "barrier"), ("web", "v1", ""), ("v1", "ddb", ""), ("v2", "vman", "manifest"),
        ("ddb", "ebr", "Stream"),
        ("f7", "ddb", ""), ("f7", "signal", "notify"), ("signal", "f8", "via agents"),
        ("anon", "fanon", ""), ("f9", "ddb", ""), ("f10", "ddb", "close STATION"),
        ("f11", "ddb", "TTL cascade"), ("f11", "llmq", "publish-first"),
        ("bedrock", "gemr", "keywords"), ("kem", "g5", "stations"),
    ]
    for s, t, lbl in sync:
        d.edge(s, t, lbl, "sync")
    asyncs = [
        ("g2", "g3", "EB"), ("g2", "g4", "EB"), ("gos", "g6", ""),
        ("vman", "f7", "SQS FIFO"), ("ebr", "g6", ""), ("ebr", "f10", ""), ("ebr", "f11", ""),
        ("f8", "frq", "EB"), ("frq", "f9", ""), ("f9", "anon", "notify"), ("fanon", "f10", "EB"),
    ]
    for s, t, lbl in asyncs:
        d.edge(s, t, lbl, "async")

    d.legend(40, 660)
    d.edge_legend(40, 1300)
    return d


if __name__ == "__main__":
    build_detailed(notes=False).write(os.path.join(OUT, "architecture.drawio"))
    build_detailed(notes=True).write(os.path.join(OUT, "architecture-complete.drawio"))
    build_global().write(os.path.join(OUT, "architecture-global.drawio"))
    print("OK: architecture.drawio, architecture-complete.drawio, architecture-global.drawio")
