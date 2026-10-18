---
name: fuentes-normativas-es
description: "Investigar y mantener información vigente sobre permisos parentales, nacimiento, prestaciones, ayudas, fiscalidad, escolarización infantil y trámites estatales, autonómicos y municipales en España. Usar al validar importes, plazos, elegibilidad o cambios normativos."
---

# Verificación de fuentes normativas españolas

Usa esta skill antes de incorporar o cambiar una afirmación legal, un importe, requisito, plazo, calendario de convocatoria o enlace administrativo en el planificador.

## Procedimiento

1. **Delimita la pregunta.** Anota la gestión, quién podría solicitarla, número de bebés, territorio (incluido municipio si aplica), fecha relevante y convocatoria o periodo. Distingue fecha prevista de parto y fecha efectiva.
2. **Localiza la fuente primaria.** Consulta, según competencia:
   - BOE y normativa publicada oficialmente para legislación estatal.
   - Seguridad Social/INSS para prestaciones y permisos gestionados por esos organismos.
   - AEAT para deducciones, declaraciones y trámites tributarios.
   - Boletín y portal oficiales de la comunidad autónoma para ayudas y escolarización autonómicas.
   - Ayuntamiento y boletín municipal para escuelas, ayudas y trámites locales.
   - Organismos oficiales de educación, sanidad y Registro Civil para sus procedimientos.
3. **Comprueba vigencia, no solo el texto.** Contrasta publicación y modificaciones, fecha de entrada en vigor, régimen transitorio, ejercicio fiscal/curso, apertura y cierre de convocatoria y territorio. Una noticia o página explicativa no reemplaza la norma o convocatoria aplicable.
4. **Extrae condiciones completas.** Registra beneficiarios, residencia/empadronamiento, plazos, incompatibilidades, documentación, método de solicitud, cuantía y excepciones pertinentes. Separa el derecho legal general de los requisitos de una ayuda concreta.
5. **Registra trazabilidad por afirmación.** Usa como mínimo:
   - `source_url` y organismo emisor;
   - territorio y tipo de trámite;
   - `checked_at` (fecha de consulta);
   - `valid_from` y, si se conoce, `valid_until`;
   - referencia normativa/convocatoria;
   - regla de plazo y cuantía con unidad y condiciones;
   - estado: verificado, pendiente de revisión, vencido o no confirmado.
6. **Determina la fecha del calendario.** Expresa la fórmula y el evento que la activa. Si no existe fecha legal única, muestra una recomendación como tal, explica su fundamento y enlaza la convocatoria. No conviertas expresiones vagas (“en primavera”, “inmediatamente”) en una fecha límite cierta.
7. **Compara con los datos existentes.** Identifica campos obsoletos, sin fuente o contradictorios, incluidas copias en código, JSON, documentación y tests. No actualices una sola copia dejando las demás desincronizadas.
8. **Propón actualización segura.** Una tarea periódica puede comprobar disponibilidad, metadatos, boletines o cambios; no demuestra actualización en tiempo real ni que una página HTML modificada cambie la ley. Emite alertas para revisión humana y registra evidencias antes de publicar una modificación.
9. **Comunica incertidumbre.** Si la fuente oficial falta, es ambigua, no está accesible o no confirma una condición, no infieras el dato. Marca el resultado como no confirmado y señala qué organismo/persona debe verificarlo.

## Monitor de publicaciones del proyecto

El workflow `.github/workflows/monitor-official-sources.yml` ejecuta `update_regulations.py` los días 1 y 16 de cada mes (aproximadamente cada 15 días) contra `fuentes_oficiales.json`. Incluye RSS del BOE/BOCM y texto visible de páginas oficiales de Seguridad Social/INSS, Justicia, AEAT y servicios de la Comunidad de Madrid. Una referencia con formato `reference` permanece listada, pero se excluye de la consulta automática cuando no se pudo validar una ruta/canal accesible; actualmente ocurre con el portal de Alcobendas (HTTP 403).

El monitor abre incidencias ante entradas nuevas/modificadas y errores de consulta. Una fuente inaccesible ya no detiene las demás: registra el fallo, conserva la última línea base correcta y el workflow crea/comenta una incidencia; los errores de configuración global siguen fallando el job. Un cambio HTML puede ser editorial o técnico: es una señal para investigar, no una conclusión jurídica. El monitor no actualiza el catálogo de reglas, no confirma la vigencia de normas ni garantiza cobertura completa. La primera ejecución solo establece la línea base.

## Límites

- No uses una cifra de una respuesta anterior, archivo local o ejemplo del usuario como evidencia de vigencia.
- No afirmes que no hay cambios solo porque una petición HTTP funciona o porque no cambió el HTML.
- No sugieras que el planificador sustituye asesoramiento profesional ni la resolución de la administración.
- No incluyas datos personales de la familia en búsquedas o herramientas externas.

## Resultado esperado

Devuelve una ficha por gestión con: jurisdicción, resumen sencillo, quién podría solicitarla, condiciones conocidas y pendientes, cuantía si está verificada, plazo/regla, documentos, enlace oficial, fecha de consulta, periodo de vigencia y estado de confianza. Distingue con claridad “confirmado”, “requiere datos” y “pendiente de verificación”.
