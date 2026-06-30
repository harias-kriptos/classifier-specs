# Guía de estilo base — Diagramador

> Fuente de verdad del estilo visual. Consultar SIEMPRE antes de crear un diagrama.
> Cada vez que el usuario enseñe un diagrama, agregar/refinar reglas aquí (sin duplicar).

_Estado: BASE — sin ejemplos registrados todavía. A medida que el usuario enseñe
diagramas, registrar sus reglas aquí y guardar los ejemplos en `referencias/ejemplos/`._

**Idioma:** etiquetas en español, mayúsculas en nombres de proceso (estilo del usuario).
**Fuente:** `Helvetica` en todo. **Lienzo:** `grid=1`, `gridSize=10`, página A4
(827×1169) como referencia; el contenido se extiende libremente. `shadow=0`.

## Tipos de diagrama soportados (y su plantilla)

| Tipo | Cuándo |
|------|--------|
| **Arquitectura AWS** (íconos aws4) | infra detallada, cuentas, VPCs |
| **Modelo C4** (Contexto/Contenedor/Componentes) | vistas de alto nivel |
| **Flowchart funcional** | lógica de negocio paso a paso |
| **Step Function / máquina de estados** | orquestación AWS |
| **Tabla / matriz de respuestas** | mapeos código→resultado |

Cuando un diagrama es multipágina, usar una página por nivel C4 (Contexto →
Contenedor → Componentes → Detalle/Infra). Mantener esa convención.

---

## 1. Arquitectura AWS (shape=mxgraph.aws4.*)

### 1.1 Íconos de servicio (`resIcon`) — color por familia (oficial AWS)
`shape=mxgraph.aws4.resourceIcon; strokeColor=#ffffff; fontColor=#232F3E;
aspect=fixed; verticalLabelPosition=bottom; verticalAlign=top; align=center;`
Tamaño **42×42** en diagramas densos, **78×78** en vistas amplias.

| Familia | Servicios | fillColor |
|---------|-----------|-----------|
| Cómputo (naranja) | Lambda, ECS, EC2/m5 | `#ED7100` (alt `#D05C17`) |
| App Integration (rosa) | API Gateway, SQS, EventBridge | `#E7157B` (alt `#BC1356`) |
| Almacenamiento (verde) | S3 | `#7AA116` |
| Base de datos (morado) | DynamoDB, RDS, VPC Endpoints | `#4D27AA` |
| Redes (morado claro) | NLB, ALB, TGW, Direct Connect, PrivateLink, TGW-attachment | `#8C4FFF` (TGW/DX a veces `#5A30B5` con gradiente `#945DF2`) |
| Seguridad/Identidad (rojo) | Cognito, IAM, KMS, Secrets Mgr | `#DD344C` (alt `#C7131F`) |
| Analítica (morado-rosa) | Glue, DMS | `#C925D1` / `#8C4FFF` |
| Internet / genérico | internet_alt1 | `#232F3E` |
| Servidor tradicional | traditional_server | `#5A30B5` |

Algunos íconos llevan `gradientColor` (ej. TGW `#5A30B5`→`#945DF2`,
`gradientDirection=north`). Variante de compute alterna `#D86613`/`#D05C17`.

### 1.1b Otras formas de servicio que aparecen
- **Íconos AWS3 (legacy)** para datos: `mxgraph.aws3.rds_db_instance`,
  `rds_db_instance_standby_multi_az`, `dynamo_db`, `oracle_db_instance`.
- **AWS4 adicionales**: `endpoints` (VPC Endpoint), `transit_gateway_attachment`,
  `snapshot`, `glacier_deep_archive` (archivado), `rds_proxy`, `role` (IAM role),
  `users`, `m5_instance` (EC2).
- **Office** (on-prem/servidores): `mxgraph.office.servers.{mainframe,
  reverse_proxy, file_server, sql_server, database_server, cluster_server}`,
  `office.databases.database_server`, `office.sites.website_public`,
  `office.devices.{mac_client, cell_phone_generic}` — relleno gris `#505050`.
- **Otras librerías**: `mxgraph.kubernetes.icon` (EKS/k8s),
  `mxgraph.mscae.enterprise.firewall`, `mxgraph.cisco_safe.compositeIcon`,
  `mxgraph.ios7.misc.iphone` (cliente móvil).
- **Genéricas de flujo**: `shape=process` (cajas de proceso),
  `rhombus`, `swimlane` (carriles), `mxgraph.arrows2.arrow` (flecha-bloque),
  `mxgraph.flowchart.{decision, terminator, start_1, start_2}`.

### 1.1c Íconos de BASES DE DATOS — librería propia (PREFERIR ESTO)
Hay una **librería de íconos de marca** ya hecha en `referencias/iconos/`. Las URIs
listas para pegar están en `referencias/iconos/_uris.json`; vista previa en
`_preview.png`; paleta arrastrable en `iconos/iconos-bd.drawio`.

> ⚠️ **FORMATO DE IMAGEN CRÍTICO (no equivocarse):**
> - Usar **PNG**, no SVG. draw.io **no renderiza** SVG embebido.
> - La data-URI debe ser `data:image/png,<base64>` — **con coma y SIN `;base64`**.
>   El formato `data:image/png;base64,…` **se rompe** porque draw.io separa los
>   estilos por `;` y parte el atributo `image=`. Los SVG de `iconos/*.svg` se
>   renderizan a PNG (p. ej. con `qlmanage -t -s 256 -o /tmp icono.svg`) y se
>   embeben en ese formato.
> - `_uris.json` ya guarda las URIs en el formato correcto (PNG, con coma).

**Para usar un ícono:** toma la data-URI de `_uris.json[<motor>]` y ponla en
`style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;aspect=fixed;
imageAspect=0;image=<URI>;fontSize=11;fontStyle=1;fontColor=#232F3E;"` con
`value="<Nombre>"`, geometría típica 48×48.

Todos los íconos son **logos oficiales de marca** (Devicon / iconos oficiales de
AWS / Simple Icons). Los logos a color van sobre una **baldosa blanca redondeada**;
los de AWS (DynamoDB) y EKS conservan su baldosa de marca con glifo blanco.

| Motor | Archivo | Estilo de baldosa | Logo |
|-------|---------|-------------------|------|
| EKS | `eks.svg` | naranja `#ED7100`, glifo blanco | rueda Kubernetes (AWS) |
| MongoDB | `mongodb.svg` | blanca | hoja MongoDB oficial (verde) |
| MySQL | `mysql.svg` | blanca | delfín MySQL oficial (teal) |
| PostgreSQL | `postgresql.svg` | blanca | elefante PostgreSQL oficial |
| DynamoDB | `dynamodb.svg` | degradado AWS `#2E27AD→#527FFF`, glifo blanco | ícono AWS DynamoDB oficial |
| Redis | `redis.svg` | blanca | logo Redis oficial (cubo rojo) |
| OpenSearch | `opensearch.svg` | azul `#005EB8`, glifo blanco | marca OpenSearch oficial |
| SQL Server | `sqlserver.svg` | blanca | logo SQL Server oficial (rojo) |
| Sybase | `sybase.svg` | blanca | logo SAP (Sybase ASE) |

Alternativa rápida si no se quiere imagen: cilindro `shape=cylinder3;size=12;
boundedLbl=1;fontColor=#fff;fontStyle=1;` con el color de marca de la tabla.
Para datastores AWS también existe el ícono `aws4` (DynamoDB `aws4.dynamodb`).

### 1.1d EKS / Kubernetes — ⚠️ importante
El `resIcon` `aws4.elastic_kubernetes_service` **NO renderiza** en algunas
versiones de draw.io (sale vacío). Por eso EKS usa el ícono propio
`referencias/iconos/eks.svg` embebido como imagen (ver tabla arriba).
**Fargate** sí funciona con `aws4.fargate`. Regla general: si un `resIcon`
`aws4` no aparece, sustituirlo por un SVG embebido en `iconos/`.

### 1.2 Contenedores de agrupación (`shape=mxgraph.aws4.group`, `fillColor=none`)
Borde + texto del mismo color, etiqueta arriba-izquierda (`align=left;
verticalAlign=top; spacingLeft=30`).

| grIcon | Representa | stroke + fontColor | dashed |
|--------|-----------|--------------------|--------|
| `group_aws_cloud` / `_alt` | Nube AWS completa | `#232F3E` (o `#66B2FF`) | 0 |
| `group_region` | Región (us-east-1) | `#147EBA` | 1 |
| `group_availability_zone` | AZ | `#444446`/`#545B64` | 1 |
| `group_vpc` | VPC | `#879196` | 0 |
| `group_security_group` | Security Group | (verde/rojo según uso) | 1 |
| `group_account` | Cuenta AWS | `#CD2264` (o `#2E7D32` verde) | 0 |
| `group_corporate_data_center` | Data Center on-prem | `#5A6C86` | 0 |
| `group_on_premise` | On-premise | `#999900` | 0 |
| `group_aws_step_functions_workflow` | Workflow SF | `#CD2264` | 0 |
| `group_ec2_instance_contents` | Contenido de EC2 | gris | 1 |
| `group_auto_scaling_group` | Auto Scaling Group | `#D86613` (naranja) | 1 |

**`groupCenter`** (`shape=mxgraph.aws4.groupCenter; grStroke=1; dashed=1;
spacingTop=25;`): agrupación con ícono centrado arriba; mismo esquema de color
que el grupo (ej. ASG naranja `#D86613`). Útil para clústeres/auto-scaling.

### 1.3 On-premise / cajas de sistema
- **Contenedor on-prem** (rounded): relleno translúcido `fillOpacity` 20–40,
  amarillo `#ffff88`/`#999900` o gris `#f5f5f5`/`#666666`. `strokeWidth=2`,
  `fontStyle=1`, etiqueta arriba.
- **Sistema/servidor opaco**: `rounded=1; fillColor=#8C8C8C; strokeColor=#6C6C6C;
  fontColor=#FFFFFF; fontStyle=1;` — o servidores office (`#505050`,
  `mxgraph.office.servers.cluster_server`, `.website_public`).
- **Firewall**: `shape=mxgraph.networks.firewall; fillColor=#FF3333;
  strokeColor=#990000;`.

## 2. Modelo C4 (shape=mxgraph.c4.*)

Colores azules corporativos, texto blanco, descripción en gris claro dentro de la caja.

| Elemento | Estilo |
|----------|--------|
| **Persona/actor** | `shape=mxgraph.c4.person2; fillColor=#083F75; strokeColor=#06315C; fontColor=#fff;` |
| **Software System** | `rounded=1; arcSize=10; fillColor=#1061B0; strokeColor=#0D5091; fontColor=#fff;` |
| **Container** | `rounded=1; arcSize=10; fillColor=#23A2D9; strokeColor=#0E7DAD; fontColor=#fff;` |
| **Web app** | `shape=mxgraph.c4.webBrowserContainer2; fillColor=#23A2D9; strokeColor=#118ACD;` |
| **Base de datos** | `shape=cylinder3; size=15; fillColor=#23A2D9; strokeColor=#0E7DAD; fontColor=#fff;` |
| **Boundary (límite de sistema)** | `rounded=1; dashed=1; dashPattern=8 4; arcSize=20; fillColor=#dae8fc; strokeColor=#6c8ebf;` (o `fillColor=none; strokeColor=#666666; strokeWidth=5`) etiqueta abajo-izquierda |

- Etiquetas C4 con plantilla `objeto placeholders`: **nombre 16px negrita**, tipo
  `[%c4Type%: %c4Technology%]`, descripción 11px gris `#cccccc`/`#E6E6E6`.
- Título de página C4: texto grande **40px** "Arquitectura" + subtítulo
  `[System Context/Container] …` a **23px**.
- Conectores C4: `curved=1` permitido, con etiqueta describiendo la relación.
- **Componentes C4** (vistas "…_Componentes"): cajas `shape=module;
  align=left; spacingLeft=20; verticalAlign=top;` (relleno por defecto/blanco),
  agrupadas dentro de boundaries; representan módulos/componentes internos.
- **Logos** (página tipo "DiagramaLogos" o esquinas): `shape=image;` con
  `image=data:image/png,<base64>` (formato con coma, ver ⚠️ en §1.1c). Embeber
  solo los logos que el usuario provea para el diagrama en cuestión.

## 3. Flowchart funcional

- **Proceso**: `rounded=1; absoluteArcSize=1; arcSize=14; strokeWidth=2;` coloreado
  por naturaleza del paso:
  - **Consulta** (CONSULTAR): gris `#f5f5f5` / `#666666` / fontColor `#333333`.
  - **Acción/escritura** (ADICIONAR, GENERAR): verde `#d5e8d4` / `#82b366`.
  - **Salida/retorno** (RETORNAR): amarillo `#fff2cc` / `#d6b656`.
  - **Error** (GESTIÓN DEL ERROR): rojo `#f8cecc` / `#b85450`.
- **Decisión**: `shape=mxgraph.flowchart.decision` (rombo), pregunta en mayúsculas.
- **Inicio/Fin**: `mxgraph.flowchart.start_1` / `mxgraph.flowchart.terminator`.
- **Conector fuera de página**: `ellipse; rounded=1; arcSize=50;` con número grande
  (36px); rojo `#f8cecc`/`#b85450` (conector ①) o azul `#99CCFF`/`#141be6` (②).
- Flechas de decisión etiquetadas **SI / NO**.
- Flecha-bloque grande (transferencia): `shape=mxgraph.arrows2.arrow`.
- Notas explicativas: caja de texto `text;` sin borde, alineada al elemento.

## 4. Step Function / máquina de estados

- **Inicio/Fin**: `ellipse; fillColor=#1A5490; fontColor=#fff; fontStyle=1;`.
- **Input**: `rounded=1; dashed=1; fillColor=#F0F4F8; strokeColor=#A0B0C0;`.
- **Estados** (paleta estándar draw.io):
  - Pass/transformación: `#DAE8FC` / `#6C8EBF` (azul).
  - Task (Lambda existente): `#D5E8D4` / `#82B366` (verde).
  - Task (Lambda nueva): `#F8CECC` / `#B85450` (rojo).
  - Choice/decisión: `rhombus; #FFF2CC / #D6B656` (amarillo).
- **Carriles de rama** (lanes): `rounded=1; dashed=1;` translúcidos, un color por rama.
- **Leyenda**: caja blanca `#CCCCCC` con muestras de color + etiqueta de cada tipo.
- **Notas de estado**: texto gris `#666666` 9px, alineado bajo cada estado, con
  viñetas `•` o detalle de entrada/salida.

## 5. Tablas / matrices

- **Encabezado**: celdas `#E1D5E7` / `#9673A6`, `fontStyle=1`, 10px.
- **Cuerpo**: celdas blancas, borde del color del tema (`#9673A6`).
- **Celda de resultado**: coloreada por outcome — verde `#D5E8D4` (OK),
  gris `#F5F5F5` (neutro), rojo `#F8CECC` (error).

## 6. Conectores (edges) — reglas transversales

- Base: `edgeStyle=orthogonalEdgeStyle; rounded=0; html=1; endArrow=classic;`
  (en C4 se permite `rounded=1`/`curved=1`). Etiquetas a `fontSize=7–10`.
- **Color = semántica del flujo:**
  - Flujo principal: `#1A5490` (azul) `strokeWidth=2`, o negro.
  - Rama/éxito: `#82B366` / fontColor `#3F7C30` (verde).
  - Token / OAuth (dashed): `#1A8C3A` (verde) o `#9673A6` (morado).
  - Error / fallback (dashed): `#B85450` (rojo).
- Etiqueta de paso con círculo: `①`, `②`… Etiquetas con condición lógica
  (`SI`/`NO`, códigos de retorno, etc.).
- Etiquetas con fondo blanco (`background=#FFFFFF`) cuando cruzan elementos.
- Usar `<Array as="points">` y `exitX/Y` · `entryX/Y` para rutas limpias sin cruces.
- **Punteados** (`dashed=1`): patrón típico `dashPattern=8 4` (boundaries/flujos
  secundarios); también `8 8` y `12 12` para distinguir niveles.
- **Bidireccionales**: `startArrow=classic` (o `startArrow=none` para línea simple)
  además de `endArrow`.
- **Flujo animado**: `flowAnimation=1` en flechas que resaltan el recorrido activo.
- **Conector tipo enlace**: `shape=link` (línea con relleno hueco) para asociaciones.
- En C4 las flechas pueden ir `rounded=1` o `curved=1`; en arquitectura/flowchart
  se mantienen ortogonales rectas.

## 7. Tipografía y textos

- Jerarquía: **48/45/40** (títulos grandes de página) · **23** (subtítulo C4) ·
  **18** (título flujo) · **16** (nombre C4) · **14** (título arquitectura) ·
  **12** (tamaño POR DEFECTO en diagramas de arquitectura: etiquetas de ícono,
  grupos, servidores) · **11** (descripciones, containers C4) · **9–10** (notas,
  estados, tabla) · **7–8** (etiquetas de flecha en diagramas muy densos).
- Regla práctica: en arquitectura/C4 amplia el cuerpo va a **12**; solo bajar a
  **7–8** cuando el diagrama es muy denso y hay que apretar.
- Negrita (`fontStyle=1`) en títulos, nombres de sistema y encabezados.
- Cursiva gris (`fontColor=#9E9E9E; fontStyle=2`) en notas al pie.
- Separadores en texto con `·` (punto medio). Saltos de línea con `&#xa;`.
- Marcas de estado en etiquetas: `✅` (existente/listo) `❌` (nuevo/pendiente),
  con fecha entre paréntesis cuando aplica (`(2026-05-08)`).

## 8. Inventario de ejemplos (`referencias/ejemplos/`)

- **Fase 1 Scan & Match** (Classifier, ref. del usuario 2026-06-30) — flujo AWS
  horizontal por estación. Reglas que aporta (ya integradas arriba): **agentes como
  "software system"** = caja gris opaca (`#8C8C8C`/`#6C6C6C`, texto blanco, descripción
  multilínea, etiqueta arriba) §1.3; **notas JSON request/response** = caja `#F5F5F5`/`#9E9E9E`
  font 9 align-left; **post-its** amarillos `#FFF8E1`/`#D9A406` para to-dos/aclaraciones;
  EMR/lambda con su ticket en la etiqueta. Reproducido con el engine determinístico
  (`context/classifier-v2/diagrams/build_phase1_scan_match.py` → `phase1-scan-match.drawio`).
