# 📋 AUDIT — Archivos que necesitan actualización

> **Status:** Auditoría 2026-05-28 post-consolidación  
> **Objetivo:** Mapear qué archivos están desactualizados y qué requiere cambio

---

## 🔍 Estado de cada archivo

| Archivo | Última actualización | Status | Acción requerida |
|---|---|---|---|
| **CONSOLIDATION-INDEX.md** | 2026-05-28 | ✅ ACTUAL | Ninguna |
| **CHANGELOG.md** | 2026-05-28 | ✅ ACTUAL | Ninguna |
| **ecosystem.md** | Pre-refresh | 🟡 PARCIAL | Actualizar: quitó mención de "Fase 1.5", aclarar Fase 1 validación + Fase 2 |
| **current-decisions.md** | Pre-refresh | 🟡 PARCIAL | Actualizar: DDB única (`classifier-cycles-state`), no `gse-cycles-samples`, 2 monorepos |
| **dev-tickets.md** | 2026-05-19 | 🟡 PARCIAL | Actualizar: agregar KT-17024/25/26/27 (validación) + KT-17028-33 (GSE) |
| **devops-tickets.md** | 2026-05-19 | 🟡 PARCIAL | Actualizar: agregar 15 tickets nuevos + refactorizar AC01 (monorepo vs repos separados) |
| **dashboard.html** | 2026-05-23 | 🟡 PARCIAL | Agregar KT-17024-27 (validación), KT-17028-33 (GSE), KT-17133 (cleanup), KT-17135 (docs) |
| **devops-reunion.html** | 2026-05-23 | 🟡 PARCIAL | Agregar todos los 15 tickets DevOps nuevos + consolidación 2 monorepos |
| **epicas-jira.md** | Pre-refresh | 🔴 DESACTUALIZADO | **CRÍTICO:** Dice "Fase 2 ahora es GSE" pero lista componentes viejos. Necesita rewrite completo |
| **orquestacion-backend.md** | POC anterior | 🔴 DESACTUALIZADO | **CRÍTICO:** Es el POC original. Archivo histórico. Marcar como `[DEPRECATED]` |
| **plan-trabajo.md** | 2026-05-19 | 🟡 PARCIAL | Validar que las HU sigan siendo válidas con consolidación de Fase 1 |
| **tareas-por-fase.md** | 2026-05-19 | 🟡 PARCIAL | Validar tareas (algunas estarán cubiertas por monorepos ahora) |
| **tickets-implementacion.md** | Pre-refresh | 🟡 PARCIAL | Revisar si es redundante con `dev-tickets.md` + `devops-tickets.md` |
| **tickets-source.md** | Pre-refresh | 🟡 PARCIAL | Verificar: ¿es fuente de specs o apunta a `/specs-staging/`? |
| **architecture.drawio** | TBD | ❓ DESCONOCIDO | ¿Refleja la consolidación? Revisar |
| **architecture-complete.drawio** | TBD | ❓ DESCONOCIDO | ¿Idem? |
| **historical/** | (carpeta archive) | ✅ OK | Dejar intacta — es histórico |
| **components/** | (carpeta) | 🟡 PARCIAL | Revisar si hay specs viejas aquí que deban consolidarse en `/specs-staging/` |

---

## 🎯 Prioridad de actualización

### **🔴 CRÍTICA (cambios significativos para la consolidación)**

1. **`epicas-jira.md`**
   - **Problema:** Sigue hablando de "Fase 1" (scan+match) y "Fase 2" (GSE) como separadas
   - **Debería:** Agregar Fase 1 Validación entre Fase 1 Scan+Match y Fase 2
   - **Acción:** Rewrite completo con 3 épicas claras: Fase 1 Scan+Match, Fase 1 Validación, Fase 2 GSE
   - **Responsable:** PM (con apoyo Haroldo para detalle técnico)

2. **`orquestacion-backend.md`**
   - **Problema:** Describe la arquitectura del POC original (pre-consolidación)
   - **Debería:** Estar marcado `[DEPRECATED - Historical Reference Only]`
   - **Acción:** Renamear a `_DEPRECATED_orquestacion-backend-poc.md` con nota al inicio
   - **Responsable:** Haroldo

### **🟡 IMPORTANTE (actualizar para coherencia)**

3. **`current-decisions.md`**
   - **Problema:** Menciona `gse-cycles-samples` como tabla — ahora es `classifier-cycles-state`
   - **Acción:** Actualizar sección "Storage operacional" con DDB única
   - **Responsable:** Haroldo

4. **`ecosystem.md`**
   - **Problema:** Overview es correcto pero no menciona Fase 1 Validación explícitamente
   - **Acción:** Agregar sección "Fase 1 — Validación humana" entre Scan+Match y Fase 2
   - **Responsable:** Haroldo + Plataforma Web (para detalles UI)

5. **`dev-tickets.md` + `devops-tickets.md`**
   - **Problema:** Están al 2026-05-19, faltan 11 dev + 15 infra nuevos
   - **Acción:** Consolidar con nueva estructura de monorepos (KT-17034, KT-17134)
   - **Responsable:** Haroldo (automated update from CONSOLIDATION-INDEX)

6. **`dashboard.html` + `devops-reunion.html`**
   - **Problema:** Visuales están al 2026-05-23, faltan últimos tickets + consolidación monorepos
   - **Acción:** Regenerar con nueva data (o agregar manualmente)
   - **Responsable:** Haroldo (o script si hay generador)

### **ℹ️ REVISAR (verificar si siguen siendo válidos)**

7. **`plan-trabajo.md`**
   - Validar que HU sigan siendo correctas con Fase 1 unificada
   
8. **`tareas-por-fase.md`**
   - Validar que tareas no estén duplicadas/redundantes con monorepos

9. **`tickets-implementacion.md`**
   - ¿Es redundante con dev-tickets.md? Consolidar o marcar como deprecated

10. **`architecture.drawio` + `architecture-complete.drawio`**
    - Revisar si reflejan la arquitectura consolidada

11. **`components/` folder**
    - Revisar si hay specs viejas que deban moverse a `/specs-staging/`

---

## 📊 Resumen del trabajo

| Categoría | # archivos | Acción | Estimado |
|---|---|---|---|
| Crítica (rewrite) | 2 | `epicas-jira.md`, `orquestacion-backend.md` | 4h |
| Importante (update) | 6 | `current-decisions.md`, `ecosystem.md`, `dev-tickets.md`, `devops-tickets.md`, `dashboard.html`, `devops-reunion.html` | 6h |
| Revisar | 6 | `plan-trabajo.md`, `tareas-por-fase.md`, `tickets-implementacion.md`, `.drawio` files, `components/` | 3h |
| **TOTAL** | **14+** | — | **~13h** |

---

## ✅ Archivo ya actualizado / nuevo

- ✅ `CONSOLIDATION-INDEX.md` (nuevo)
- ✅ `CHANGELOG.md` (nuevo)
- ✅ Memory del proyecto (actualizado)

---

## 🚀 Propuesta de orden

1. **Hoy (2026-05-28):** Actualizar crítica (epicas-jira, orquestacion-backend)
2. **Mañana:** Actualizar importante (dev-tickets, devops-tickets, ecosystem, current-decisions)
3. **Esta semana:** Regenerar HTML (dashboard, devops-reunion) + revisar componentes

---

**¿Hacemos esto ahora o lo dejamos como referencia para que los equipos sepan qué está desactualizado?**
