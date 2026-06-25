# Spec — EMR joyas-priorizer: rollup.json por estación

> Ticket: [KT-17588](https://kriptosteam.atlassian.net/browse/KT-17588)
> Status: draft (2026-06-24)
> Épica: **Discovery / Fase 1** (KT-16369) · Monorepo: `kriptos-io/classifier-v2-backend` (KT-17132)
> Base: add-on a `joyas-priorizer` (KT-16616, ✅)

---

## 1. Goal

Que el job EMR `joyas-priorizer` emita, además de `matches.jsonl`, un `rollup.json` compacto por estación: agregación por categoría (conteo + histograma de áreas). Mueve la agregación pesada a Spark (donde los datos ya están distribuidos) para que el consolidador (KT-17586) arme el Excel en O(#estaciones), no O(#archivos).

## 2. Non-goals

- La consolidación enterprise (KT-17586).
- Cambios al formato/contenido de `matches.jsonl`.
- Generar las categorías/keywords (KT-16859).

## 3. User-visible behavior

Output nuevo por estación: `s3://...crown_jewels/{ent}/{sta}/rollup.json`:

```json
[
  {"category_id": "plan-estrategico",
   "original_category": "Plan Estratégico Quinquenal",
   "count": 1240,
   "area_histogram": {"Dirección General": 980, "Planeación": 260}}
]
```

`matches.jsonl` no cambia (sigue siendo el detalle para expandir paths en el confirm KT-17587).

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| PySpark job `joyas-priorizer` | `groupBy(category_id).agg(count, area_histogram)` por estación + write JSON | `count` = filas matcheadas de la categoría; histograma cuenta por área. |

## 5. Inputs and outputs

- Input: el DataFrame de matches que el job ya construye (post Aho-Corasick + normalize).
- Output: un `rollup.json` por estación (una fila por `category_id`).

```python
rollup = (matches_df
          .groupBy("category_id", "original_category")
          .agg(count("*").alias("count"),
               map_from_entries(...).alias("area_histogram")))
```

## 6. Dependencies

- PySpark (ya en el job EMR).
- Sin dependencias nuevas.
- Consumidor: `crown-report-consolidator` (KT-17586).

## 7. Test plan

```
[ ] test_rollup::test_count_per_category_matches_file_count
[ ] test_rollup::test_area_histogram_counts_files_per_area
[ ] test_rollup::test_empty_station_yields_empty_array
[ ] test_rollup::test_idempotent_same_tree_same_rollup
[ ] test_e2e::test_job_writes_both_matches_and_rollup (Spark local)
```

## 8. Eval impact

No aplica (agregación determinística, sin LLM).

## 9. Threat model delta

Sin nuevo trust boundary (mismo bucket/IAM que `matches.jsonl`).

## 10. Resolved decisions

- **Pre-agregar en EMR** en vez de escanear `matches.jsonl` en el consolidador. Decisión Haroldo 2026-06-24 (preocupación de performance con miles/millones de registros).
- `category_id` + `original_category` se preservan para el join de metadata en KT-17586.

## 11. Open questions

- Ninguna abierta. (El esquema de `area_histogram` se confirma contra el output real de `joyas-priorizer`.)

## 12. Rollout

- Branch: `KT-17588-emr-rollup`
- Add-on al job EMR existente; tests Spark verdes.
- PR a `main` con `Implements specs/00X-emr-rollup.md`.
