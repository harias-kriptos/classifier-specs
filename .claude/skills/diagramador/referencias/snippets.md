# Snippets copy-paste por tipo de diagrama

> Bloques mínimos y **válidos** (parsean con `scripts/validate_drawio.py`) que
> materializan `estilo-base.md`. Copiá el bloque, duplicá las celdas que necesites
> y ajustá `value`, `x/y/width/height` e `id` (los `id` deben ser únicos).
> Regla de oro: **no arranques el XML desde cero** — partí de un snippet.

Convenciones transversales:
- Geometría: `<mxGeometry x y width height as="geometry"/>` en vértices;
  `relative="1"` en edges. Origen arriba-izquierda, +x derecha, +y abajo.
- Saltos de línea en `value`: `&#xa;`. Fuente por defecto **12** (arquitectura).
- Para íconos de BD, reemplazá `{{uri:MOTOR}}` por `_uris.json[MOTOR]`
  (formato `data:image/png,…` — ver `scripts/add_icon.py`).

---

## 0. Esqueleto base (multipágina)

Una página por nivel C4 (Contexto → Contenedor → Componentes → Infra).

```xml
<mxfile host="app.diagrams.net">
  <diagram name="Contexto" id="pg-contexto">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" page="1"
                  pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- celdas acá -->
      </root>
    </mxGraphModel>
  </diagram>
  <diagram name="Contenedor" id="pg-contenedor">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" page="1"
                  pageWidth="827" pageHeight="1169" shadow="0">
      <root><mxCell id="0"/><mxCell id="1" parent="0"/></root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

---

## 1. Arquitectura AWS

Servicio = `resourceIcon` con `fillColor` de su categoría (nunca un rectángulo).
Tamaño 78×78 en vistas amplias, 42×42 en densas. Colores en `estilo-base.md §1.1`.

```xml
<!-- Nube AWS (contenedor): todo lo AWS va adentro -->
<mxCell id="cloud" value="AWS Cloud"
  style="shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#232F3E;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="40" y="40" width="520" height="300" as="geometry"/></mxCell>

<!-- Lambda (Compute, naranja) -->
<mxCell id="fn" value="Procesar"
  style="sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;strokeColor=#ffffff;fillColor=#ED7100;aspect=fixed;verticalLabelPosition=bottom;verticalAlign=top;align=center;fontColor=#232F3E;fontSize=12;"
  vertex="1" parent="cloud"><mxGeometry x="40" y="60" width="78" height="78" as="geometry"/></mxCell>

<!-- API Gateway (App Integration, rosa) -->
<mxCell id="api" value="API Gateway"
  style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.api_gateway;strokeColor=#ffffff;fillColor=#E7157B;aspect=fixed;verticalLabelPosition=bottom;verticalAlign=top;align=center;fontColor=#232F3E;fontSize=12;"
  vertex="1" parent="cloud"><mxGeometry x="200" y="60" width="78" height="78" as="geometry"/></mxCell>

<!-- S3 (Storage, verde) -->
<mxCell id="s3" value="Bucket"
  style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.s3;strokeColor=#ffffff;fillColor=#7AA116;aspect=fixed;verticalLabelPosition=bottom;verticalAlign=top;align=center;fontColor=#232F3E;fontSize=12;"
  vertex="1" parent="cloud"><mxGeometry x="360" y="60" width="78" height="78" as="geometry"/></mxCell>
```

`grIcon` útiles: `group_region` (teal `#147EBA`, dashed), `group_vpc`
(`#879196`), `group_availability_zone`, `group_account`. Ver `estilo-base.md §1.2`.

---

## 2. Ícono de base de datos (librería propia)

`shape=image` con la data-URI de `_uris.json`. **PNG con coma**, nunca `;base64`.
Motores disponibles: mongodb · mysql · postgresql · dynamodb · redis · opensearch
· sqlserver · sybase · eks.

```xml
<mxCell id="pg" value="PostgreSQL"
  style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;aspect=fixed;imageAspect=0;image={{uri:postgresql}};fontSize=11;fontStyle=1;fontColor=#232F3E;"
  vertex="1" parent="1"><mxGeometry x="40" y="40" width="48" height="48" as="geometry"/></mxCell>
```

Alternativa sin imagen (cilindro con color de marca):
```xml
<mxCell id="db" value="Redis"
  style="shape=cylinder3;size=12;boundedLbl=1;fontColor=#ffffff;fontStyle=1;fillColor=#D82C20;strokeColor=#9B1C13;"
  vertex="1" parent="1"><mxGeometry x="120" y="40" width="60" height="70" as="geometry"/></mxCell>
```

---

## 3. Modelo C4

Azules corporativos, texto blanco, descripción gris dentro de la caja.

```xml
<!-- Persona / actor -->
<mxCell id="user" value="Usuario&#xa;[Person]&#xa;Cliente final"
  style="html=1;fontSize=11;fontColor=#ffffff;shape=mxgraph.c4.person2;align=center;metaEdit=1;points=[[0.5,0,0],[1,0.5,0],[0.5,1,0],[0,0.5,0]];resizable=0;fillColor=#083F75;strokeColor=#06315C;"
  vertex="1" parent="1"><mxGeometry x="40" y="40" width="200" height="180" as="geometry"/></mxCell>

<!-- Software System -->
<mxCell id="sys" value="Sistema&#xa;[Software System]&#xa;Hace X"
  style="rounded=1;arcSize=10;whiteSpace=wrap;html=1;fontSize=11;fontColor=#ffffff;align=center;fillColor=#1061B0;strokeColor=#0D5091;"
  vertex="1" parent="1"><mxGeometry x="320" y="60" width="200" height="120" as="geometry"/></mxCell>

<!-- Container -->
<mxCell id="cnt" value="API&#xa;[Container: Python]&#xa;Expone endpoints"
  style="rounded=1;arcSize=10;whiteSpace=wrap;html=1;fontSize=11;fontColor=#ffffff;align=center;fillColor=#23A2D9;strokeColor=#0E7DAD;"
  vertex="1" parent="1"><mxGeometry x="600" y="60" width="200" height="120" as="geometry"/></mxCell>

<!-- Base de datos C4 -->
<mxCell id="c4db" value="DB&#xa;[Container: PostgreSQL]"
  style="shape=cylinder3;size=15;whiteSpace=wrap;html=1;fontSize=11;fontColor=#ffffff;align=center;fillColor=#23A2D9;strokeColor=#0E7DAD;"
  vertex="1" parent="1"><mxGeometry x="640" y="240" width="120" height="120" as="geometry"/></mxCell>

<!-- Boundary (límite de sistema) -->
<mxCell id="bnd" value="Sistema interno"
  style="rounded=1;dashed=1;dashPattern=8 4;arcSize=20;html=1;fontSize=12;fontStyle=2;fontColor=#666666;verticalAlign=bottom;align=left;spacingLeft=10;fillColor=none;strokeColor=#666666;strokeWidth=3;"
  vertex="1" parent="1"><mxGeometry x="560" y="20" width="280" height="360" as="geometry"/></mxCell>
```

---

## 4. Flowchart funcional

Color = naturaleza del paso. Proceso `rounded`, decisión `rhombus`.

```xml
<!-- Inicio -->
<mxCell id="ini" value="Inicio"
  style="rounded=1;whiteSpace=wrap;html=1;arcSize=40;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="80" y="40" width="120" height="40" as="geometry"/></mxCell>

<!-- Proceso CONSULTA (gris) -->
<mxCell id="p1" value="CONSULTAR datos"
  style="rounded=1;absoluteArcSize=1;arcSize=14;strokeWidth=2;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="60" y="120" width="160" height="50" as="geometry"/></mxCell>

<!-- Proceso ACCIÓN (verde) -->
<mxCell id="p2" value="GENERAR resultado"
  style="rounded=1;absoluteArcSize=1;arcSize=14;strokeWidth=2;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="60" y="320" width="160" height="50" as="geometry"/></mxCell>

<!-- Decisión (rombo) -->
<mxCell id="dec" value="¿EXISTE?"
  style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="80" y="210" width="120" height="80" as="geometry"/></mxCell>

<!-- Conector fuera de página -->
<mxCell id="off" value="1"
  style="ellipse;rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=36;fontStyle=1;"
  vertex="1" parent="1"><mxGeometry x="280" y="220" width="60" height="60" as="geometry"/></mxCell>

<!-- Edge de decisión con etiqueta SI/NO -->
<mxCell id="eSi" value="SI" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;fontSize=10;" edge="1" parent="1" source="dec" target="p2"><mxGeometry relative="1" as="geometry"/></mxCell>
```

---

## 5. Step Function / máquina de estados

```xml
<!-- Inicio / Fin -->
<mxCell id="start" value="Start"
  style="ellipse;whiteSpace=wrap;html=1;fillColor=#1A5490;strokeColor=#0D2F50;fontColor=#ffffff;fontStyle=1;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="80" y="40" width="100" height="50" as="geometry"/></mxCell>

<!-- Task: Lambda existente (verde) -->
<mxCell id="t1" value="Validar"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="70" y="130" width="120" height="50" as="geometry"/></mxCell>

<!-- Task: Lambda nueva (rojo) -->
<mxCell id="t2" value="Enriquecer (nuevo)"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8CECC;strokeColor=#B85450;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="70" y="220" width="120" height="50" as="geometry"/></mxCell>

<!-- Choice (amarillo) -->
<mxCell id="ch" value="¿OK?"
  style="rhombus;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=12;"
  vertex="1" parent="1"><mxGeometry x="80" y="310" width="100" height="70" as="geometry"/></mxCell>

<!-- Leyenda -->
<mxCell id="leg" value="Leyenda&#xa;verde = existente&#xa;rojo = nuevo"
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#CCCCCC;align=left;verticalAlign=top;spacingLeft=8;fontSize=10;"
  vertex="1" parent="1"><mxGeometry x="320" y="40" width="180" height="80" as="geometry"/></mxCell>
```

---

## 6. Tabla / matriz de respuestas

```xml
<mxCell id="th1" value="Código"
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontStyle=1;fontSize=10;"
  vertex="1" parent="1"><mxGeometry x="40" y="40" width="120" height="30" as="geometry"/></mxCell>
<mxCell id="th2" value="Resultado"
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontStyle=1;fontSize=10;"
  vertex="1" parent="1"><mxGeometry x="160" y="40" width="160" height="30" as="geometry"/></mxCell>
<mxCell id="c11" value="200"
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#9673A6;fontSize=10;"
  vertex="1" parent="1"><mxGeometry x="40" y="70" width="120" height="30" as="geometry"/></mxCell>
<mxCell id="c12" value="OK"
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#9673A6;fontSize=10;"
  vertex="1" parent="1"><mxGeometry x="160" y="70" width="160" height="30" as="geometry"/></mxCell>
```

---

## 7. Conectores (edges) — color = semántica

```xml
<!-- Síncrono: línea sólida, flecha llena -->
<mxCell id="es" value="invoca"
  style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;strokeColor=#1A5490;strokeWidth=2;fontSize=9;"
  edge="1" parent="1" source="api" target="fn"><mxGeometry relative="1" as="geometry"/></mxCell>

<!-- Asíncrono / evento: dashed rosa, flecha abierta -->
<mxCell id="ea" value="evento"
  style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;dashPattern=8 4;strokeColor=#E7157B;fontSize=9;"
  edge="1" parent="1" source="fn" target="s3"><mxGeometry relative="1" as="geometry"/></mxCell>

<!-- Token / OAuth: dashed verde -->
<mxCell id="et" value="token"
  style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;dashed=1;strokeColor=#1A8C3A;fontSize=9;"
  edge="1" parent="1" source="api" target="fn"><mxGeometry relative="1" as="geometry"/></mxCell>

<!-- Error / fallback: dashed rojo -->
<mxCell id="ee" value="error"
  style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;dashed=1;strokeColor=#B85450;fontColor=#B85450;fontSize=9;"
  edge="1" parent="1" source="fn" target="s3"><mxGeometry relative="1" as="geometry"/></mxCell>

<!-- Etiqueta de paso circulada sobre el edge -->
<mxCell id="lbl" value="①" style="text;html=1;fontSize=12;labelBackgroundColor=#FFFFFF;" vertex="1" connectable="0" parent="es"><mxGeometry x="-0.2" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>
```

Para rutas limpias sin cruces: `exitX/exitY` + `entryX/entryY` en el style del
edge, y `<Array as="points">` con waypoints. Ver `estilo-base.md §6`.
