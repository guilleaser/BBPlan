# Planificador Familiar de Gestiones y Bajas por Nacimiento

Prototipo web estático para explorar un planificador de trámites por nacimiento. **No es actualmente una fuente fiable de asesoramiento ni de plazos oficiales.** Sus cantidades, duración de permisos, elegibilidad y fechas no tienen trazabilidad normativa suficiente.

## Características

- Incluye pantallas de ejemplo para número de bebés, comunidad autónoma, permisos y gestiones.
- El timeline y checklist actuales son **demostrativos y no verificados**; la exportación de calendarios está deshabilitada hasta validar las reglas y fechas.
- Las vacaciones se configuran por separado para cada progenitor. La lactancia muestra el hito general de 9 meses y la posible extensión legal hasta 12 meses bajo sus condiciones; los días acumulados son estimaciones que deben confirmarse con la empresa o convenio.
- Las fechas calculadas de lactancia y vacaciones cuentan días de lunes a viernes, sin descontar festivos; no sustituyen el calendario laboral aplicable.
- Puede desplegarse en proveedores con planes gratuitos; sus límites y condiciones pueden cambiar.

## Publicar en GitHub y activar los workflows

La web estática se publica con GitHub Pages desde `index.html`; no necesita un proceso de compilación. El workflow de Pages se ejecuta al hacer push a `main`. El monitor de fuentes corre los días 1 y 16 de cada mes y se puede lanzar manualmente.

### 1. Crear un repositorio

1. Inicia sesión en [GitHub](https://github.com/new) y crea un repositorio llamado, por ejemplo, `BBPlan`.
2. Para publicar GitHub Pages sin coste, el plan Free requiere que el repositorio sea **público**. El código y el catálogo de fuentes quedarán visibles. No subas datos reales de embarazo, salud, empleo, identidad, ingresos, contraseñas ni secretos.
3. Créalo vacío: no marques las opciones para añadir README, `.gitignore` o licencia, porque este proyecto ya tiene archivos.

### 2. Subir este proyecto desde Windows

Abre PowerShell en la carpeta del proyecto y sustituye `TU_USUARIO` por tu usuario de GitHub:

```powershell
Set-Location "C:\Users\Guillermo\Documents\BBPlan"
git init -b main
git add .
git commit -m "Initial BBPlan website and official-source monitor"
git remote add origin https://github.com/TU_USUARIO/BBPlan.git
git push -u origin main
```

Si Git solicita identidad y todavía no la has configurado, configura el nombre y correo que quieras utilizar para tus commits y repite el commit:

```powershell
git config --global user.name "Tu nombre"
git config --global user.email "TU_CORREO_O_NOREPLY_DE_GITHUB"
```

En el primer `git push`, GitHub puede pedir que inicies sesión en el navegador. Si el nombre del repositorio no es `BBPlan`, usa exactamente el mismo nombre en la URL del remoto.

### 3. Habilitar GitHub Actions y el monitor

1. En el repositorio, abre **Settings → Actions → General**.
2. En **Actions permissions**, permite las GitHub Actions necesarias para ejecutar los workflows del repositorio.
3. En **Workflow permissions**, selecciona **Read and write permissions** y guarda. El monitor necesita crear incidencias y guardar su línea base de fuentes. No necesita un token personal ni secretos.
4. Abre **Actions** y confirma que aparecen `Monitor official sources` y `Deploy website to GitHub Pages`.
5. Selecciona `Monitor official sources` → **Run workflow** → rama `main` → **Run workflow** para hacer la primera comprobación ahora. La primera ejecución establece la línea base y no notifica como nuevas las publicaciones que ya estaban presentes. Revisa su resumen y artefacto; si termina con error, consulta la incidencia de alerta y el log.
6. Suscríbete a las notificaciones del repositorio/incidencias para enterarte de las publicaciones detectadas. Las comprobaciones automáticas siguientes están programadas para los días 1 y 16; GitHub puede retrasar o saltarse ejecuciones programadas.

### 4. Publicar con GitHub Pages

1. Abre **Settings → Pages**.
2. En **Build and deployment → Source**, selecciona **GitHub Actions**.
3. Ve a **Actions → Deploy website to GitHub Pages** y pulsa **Run workflow** si el primer push no lo ha iniciado.
4. Espera a que el workflow termine correctamente. La URL aparecerá en **Settings → Pages** y en el resumen del despliegue. Para un repositorio llamado `BBPlan`, normalmente será `https://TU_USUARIO.github.io/BBPlan/`.
5. Abre la URL en el navegador. Cada push futuro a `main` vuelve a desplegar `index.html`.

Los workflows son independientes: Actions puede guardar una nueva línea base sin provocar otro workflow por ese push automatizado. Esto no afecta al sitio, porque la línea base no forma parte de la web publicada.

## Monitorización de fuentes oficiales

El workflow `.github/workflows/monitor-official-sources.yml` consulta el día 1 y 16 de cada mes (aproximadamente cada 15 días) los feeds y páginas oficiales configurados en [`fuentes_oficiales.json`](./fuentes_oficiales.json). Incluye BOE, BOCM, Seguridad Social/INSS, Ministerio de Justicia, AEAT y páginas de la Comunidad de Madrid para natalidad, admisión y becas infantiles y tarjeta sanitaria. Compara nuevas entradas RSS y texto visible de páginas; una modificación puede ser editorial o técnica y requiere revisión humana.

Si detecta cambios, abre una incidencia para revisión; también alerta si no pudo consultar una fuente. Una URL rota ya no aborta el chequeo completo: registra el error, conserva la última línea base conocida de esa fuente, sigue con las demás y añade el problema al informe/incidencia. Errores de configuración inválida siguen deteniendo el workflow. Ejecuta pruebas, guarda un informe como artefacto y conserva la línea base en `normative_sources_state.json`. El archivo incluido en este proyecto contiene una línea base inicial de las diez fuentes accesibles, consultadas el 18 de octubre de 2026; Alcobendas figura aparte como referencia no monitorizada. La primera ejecución en GitHub comparará las fuentes con esa línea base y **no** certificará que los datos de la web sean correctos.

Para activarlo, publica el proyecto en GitHub, habilita Actions y permite al `GITHUB_TOKEN` escribir contenidos e incidencias (Settings → Actions → General → Workflow permissions: Read and write). Suscríbete a las notificaciones del repositorio/incidencias para recibir los avisos. GitHub puede retrasar o saltarse ejecuciones programadas; `workflow_dispatch` permite ejecutar el control manualmente. No requiere secretos de usuario ni envía datos familiares a las fuentes.

**Esto no actualiza automáticamente las cifras ni las reglas de la web.** Un boletín nuevo puede no afectar a este planificador; los feeds no cubren todas las páginas de INSS, Seguridad Social, AEAT, sanidad, Registro Civil, educación ni ayuntamientos. La aplicación actual mantiene datos y cálculos de ejemplo sin trazabilidad jurídica suficiente. No se debe confiar en ella para cumplir plazos oficiales hasta verificar cada trámite, regla, calendario y territorio contra su fuente primaria, incorporar esa evidencia al catálogo y probar los cálculos. No es posible garantizar el 100 % de exhaustividad o exactitud para todos los casos.

### Límites municipales y de cobertura

La selección inicial cubre fuentes estatales y autonómicas madrileñas. La fuente del Ayuntamiento de Alcobendas está registrada como referencia pendiente, pero no se monitoriza: durante la configuración respondió HTTP 403 y no se confirmó una ruta oficial específica de escuelas, ayudas o trámites de nacimiento. Por tanto, **el catálogo municipal de Alcobendas no está cubierto**. Hay que obtener una ruta oficial accesible o un feed confirmado antes de incluirla en la monitorización; no se sustituye por el portal de otro municipio.

Las páginas HTML se comparan por texto visible, lo que puede generar falsos avisos si cambia el diseño, la navegación o un texto general. Ninguna alerta es una interpretación legal. Una persona debe contrastar el acto publicado y su vigencia, determinar si afecta a una regla, registrar la fuente y actualizarla mediante un cambio revisado con pruebas. La cobertura y las reglas deben continuar marcadas como pendientes mientras esas verificaciones no estén hechas.