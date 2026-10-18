---
name: planificador-familiar-web
description: "Diseñar, auditar o implementar una web que genere calendario y checklist de trámites por embarazo o nacimiento en España, con comunidad autónoma, municipio, uno o varios bebés, permisos, guarderías, ayudas y vacaciones."
---

# Planificador web de gestiones familiares

Aplica esta skill al modelar un nuevo plan, revisar una regla, diseñar pantallas, calcular fechas o exportar el calendario.

## Procedimiento

1. **Inspecciona lo existente.** Revisa estructura, fuentes de datos, cálculos, datos de ejemplo, exportación y documentación. Busca especialmente reglas duplicadas en interfaz, JSON y script de actualización.
2. **Obtén el contexto mínimo necesario.** Considera fecha prevista/real de nacimiento, número de bebés, comunidad autónoma y municipio, progenitores y situación familiar/laboral pertinente, vacaciones disponibles, curso escolar y necesidades de guardería. Pregunta solo por lo que cambie elegibilidad o cálculo. Permite dejar una respuesta desconocida y muestra qué resultado queda pendiente.
3. **Construye una matriz de cobertura.** Evalúa, sin asumir elegibilidad, Registro Civil, inscripción sanitaria/pediatra, permisos y prestaciones, trámites laborales, beneficios fiscales, ayudas estatales/autonómicas/municipales, escuelas infantiles públicas por titularidad, guarderías y becas, y otros documentos relevantes. Para cada categoría registra aplicabilidad, datos faltantes o razón de exclusión.
4. **Verifica reglas legales** con `fuentes-normativas-es` antes de codificar importes o plazos. El calendario debe separar los plazos legales, convocatorias publicadas, hitos dependientes del nacimiento y recordatorios anticipados. No infieras que una solicitud se abre siempre en el mismo mes.
5. **Modela los datos como fuente única.** Mantén las reglas fuera de las plantillas y evita copias manuales de catálogos en HTML, scripts o README. Toda regla publicada debe tener fuente, territorio, fecha de comprobación, vigencia y condiciones. Un dato vencido/no verificado debe mostrarse con su estado y no como vigente.
6. **Calcula planes por persona y escenario.** Representa periodos de cada progenitor y sus restricciones por separado; no supongas que todo permiso puede transferirse, solaparse, fraccionarse o enlazarse de una manera concreta. Sustenta cada regla en la normativa vigente. No conviertas una cantidad estimada de lactancia en derecho fijo universal. Identifica vacaciones aportadas por el usuario como dato personalizable.
7. **Trata fechas correctamente.** Usa fechas locales sin desplazamientos UTC en entradas de fecha y eventos de día completo. Documenta el cómputo de días hábiles/naturales cuando sea aplicable, maneja años bisiestos y recalcula desde el nacimiento efectivo las acciones que dependan de él.
8. **Presenta un plan accionable.** Cada elemento debe incluir título, fecha o ventana, si es obligación/plazo oficial o recordatorio, responsable sugerido, motivo, requisitos/documentos, fuente oficial, fecha de última comprobación y estado (pendiente, completado, no aplicable o por confirmar). Mantén consistentes calendario, timeline, lista y exportación `.ics`.
9. **Protege a la familia.** Minimiza y no persistas información sensible por defecto. No envíes perfiles a APIs de terceros. Si se propone almacenamiento o sincronización, requiere consentimiento explícito y describe retención y eliminación.
10. **Valida los escenarios.** Añade pruebas de nacimiento estimado frente a real, gestación múltiple, distintas CCAA/municipios, reglas condicionales, fechas límite, año bisiesto, entradas inválidas y exportación ICS sin corrimiento de día. Verifica teclado, etiquetas, contraste y presentación móvil.

## Estado actual del proyecto

El workflow de monitorización de fuentes oficiales solo genera alertas para revisión; no publica actualizaciones legales ni recalcula la web. El prototipo contiene datos y cálculos no verificados, por lo que no debe presentarse como calendario oficial fiable ni exportar fechas de cumplimiento hasta completar la verificación por trámite y territorio. Ampliar `fuentes_oficiales.json` requiere comprobar que cada feed pertenece realmente al organismo competente y documentar qué contenido cubre y qué deja fuera.

## Principio de honestidad

“No saltarse nada” es un objetivo de cobertura, no una garantía posible. Enumera las áreas cubiertas, límites territoriales, fuentes no monitorizadas, datos que faltan y trámites que requieren confirmación oficial. Nunca rellenes huecos con importes o plazos plausibles pero no comprobados.
