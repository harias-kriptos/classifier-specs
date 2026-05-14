# Template — Jira Bug

Plantilla para la **descripción** de un Bug en Jira. Útil cuando un brainstorm parte de un bug reportado en producción.

> Reemplazar todo `{...}` con el valor real. Borrar secciones que no apliquen.

---

```markdown
## Comportamiento observado

{Qué hace el sistema HOY, en términos concretos. Incluir mensaje de error si lo hay.}

## Comportamiento esperado

{Qué debería hacer el sistema en cambio.}

## Pasos para reproducir

1. {paso 1}
2. {paso 2}
3. {paso 3}
4. **Resultado actual:** {qué se observa}
5. **Resultado esperado:** {qué se debería observar}

## Entorno

- **Ambiente:** {prod / staging / dev / local}
- **Componente:** {Lambda / API / Frontend / etc.}
- **Versión:** {commit SHA, release tag o agent_version}
- **Primera observación:** {fecha + hora UTC}
- **Frecuencia:** {1 vez / ocasional / consistente / 100%}

## Impacto

- **Severidad:** {S0 / S1 / S2 / S3}
- **Usuarios afectados:** {cantidad, segmento, o "1 enterprise específico"}
- **Funcionalidad bloqueada:** {qué no se puede hacer mientras dure}
- **Workaround temporal disponible:** {sí + qué hacer | no}

## Evidencia

- **Logs:** {paths CloudWatch / link a Splunk / extracto JSON}
- **Trazas / requestId:** {IDs específicos}
- **Screenshots / videos:** {si aplica}
- **Datos del request que falló:** {sanitizado, sin PII}

## Análisis preliminar (opcional)

{Si hay hipótesis inicial: qué línea de código, qué commit reciente, qué cambio de configuración pudo causarlo. Marcar explícitamente como hipótesis no confirmada.}

## Referencias

- **Brainstorm de refinamiento:** {link al archivo en classifier-specs/brainstorms/ si se refinó}
- **Spec del fix:** {link — agregado por Skill 02}
- **MR/PR del fix:** {link — agregado por Skill 04}
- **Incidente / postmortem:** {si aplica}

## Definition of Done

- [ ] Test de regresión escrito que reproduce el bug (RED)
- [ ] Test pasa con el fix aplicado (GREEN)
- [ ] Coverage del módulo afectado ≥ 80%
- [ ] Workaround temporal (si existe) retirado de docs/runbooks
- [ ] Causa raíz documentada en el ticket (no solo el síntoma)
- [ ] Postmortem si Severidad ≥ S2
```

---

## Notas para el agente que lo aplica

- El análisis preliminar es **opcional** y **siempre debe marcarse como hipótesis** hasta que se confirme con un test fallido.
- Severidad: S0 = caído total / data loss, S1 = funcionalidad crítica rota, S2 = funcionalidad importante rota con workaround, S3 = cosmético o edge case.
- Datos del request: si el ticket vive en Jira, sanitizar PII. Si vive en un canal interno seguro, se puede pegar crudo con un warning.
