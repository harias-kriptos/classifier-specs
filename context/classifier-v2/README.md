# Contexto del producto — Backend Classifier v2

Documentación, estado y presentaciones del backend del Classifier v2. Para verlo navegable, abrí **[`index.html`](index.html)** (portada con links a todas las presentaciones).

> **Fuente de verdad del estado:** [`STATUS.md`](STATUS.md) — 3 épicas, monorepos, tickets, modelo de infra, gaps + diagrama. **Si algo no coincide, manda STATUS.md.** De ahí se alimentan todas las presentaciones.

---

## Presentaciones — orden recomendado

**1.** Pitch → **2.** Avance → **3.** Arquitectura → **4.** Status (drill-down) · DevOps aparte.

| # | Archivo | Qué es | Para quién | Cuándo |
|---|---|---|---|---|
| 1 | 🎤 [`presentacion-clasificador.html`](presentacion-clasificador.html) | El pitch: método + trabajo + resultado (sin tickets) | Liderazgo / no técnicos | Abrir reunión, contar el porqué |
| 2 | 📈 [`avance.html`](avance.html) ⭐ | **Dónde estamos:** 3 monorepos y qué incluye cada uno, estado global, fase en curso, specs/brainstorm/tickets por épica | Liderazgo + equipo | **Reportar avance** |
| 3 | 🗺️ [`architecture.html`](architecture.html) | Diagrama end-to-end (Mermaid): Discovery → Máquina de Estados → GSE + Validación + LLM | Técnicos / DevOps | Explicar el flujo y las piezas |
| 4 | 📋 [`status.html`](status.html) | Drill-down: tablas de tickets por épica, infra, JDC, gaps | Equipo / PM | Revisar ticket por ticket |
| — | ⚙️ [`devops-reunion.html`](devops-reunion.html) | Vista DevOps: 1 monorepo por módulo + modelo de infra dentro del entregable | DevOps | Coordinar infra / repos |
| — | 📊 [`dashboard.html`](dashboard.html) | Tablero de alto nivel (se solapa con avance/status — ver nota) | Equipo | Vistazo rápido |

⭐ **`avance.html` es la principal para mostrar progreso.**

---

## Fuentes de verdad (no son presentaciones)

| Archivo | Qué es |
|---|---|
| ✅ [`STATUS.md`](STATUS.md) | Estado real del backend (markdown). De acá salen todas las presentaciones. |
| 🗃️ [`dev-tickets.md`](dev-tickets.md) | Detalle histórico del refresh 2026-05 (cómo se llegó acá). Banner que apunta a STATUS.md. |
| 🗃️ [`devops-tickets.md`](devops-tickets.md) | Inventario DevOps histórico del refresh. |

---

## Las 3 épicas (resumen)

| Épica | Jira | Monorepo | Estado |
|---|---|---|---|
| 🔍 **Discovery** | KT-16369 | `classifier-v2-backend` | Infra ✅ · 4/5 lambdas |
| ⚙️ **Máquina de Estados** | KT-17270 | `classifier-state-backend` | **En progreso** |
| 📦 **GSE** | KT-16370 | `classifier-gse-backend` | Specs listas · por arrancar |
| 🧩 **Validación** | _BE 07 futura_ | TBD | Sin crear |

Modelo: **un monorepo por módulo + infra dentro de cada entregable** (sin tickets DevOps de infra suelta).

---

## Nota: solapamiento de presentaciones

`avance.html`, `status.html` y `dashboard.html` muestran "estado" desde ángulos parecidos. Recomendación:
- **`avance.html`** → oficial de progreso (la más completa).
- **`status.html`** → drill-down ticket a ticket.
- **`dashboard.html`** → candidata a archivar/borrar para evitar ruido.

---

## Otros archivos en esta carpeta

- [`components/`](components/) — detalle por componente (phase-1, phase-2, agent).
- [`epicas-jira.md`](epicas-jira.md), [`plan-trabajo.md`](plan-trabajo.md), [`tareas-por-fase.md`](tareas-por-fase.md) — material histórico del POC/refresh.
- [`CHANGELOG.md`](CHANGELOG.md), [`CONSOLIDATION-INDEX.md`](CONSOLIDATION-INDEX.md) — histórico de consolidaciones.
