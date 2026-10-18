"""Monitor official publication feeds and report changes for human review."""

from __future__ import annotations

import hashlib
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "fuentes_oficiales.json"
STATE_FILE = ROOT / "normative_sources_state.json"
REPORT_FILE = ROOT / "monitor_report.md"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 30


class MonitorError(Exception):
    """Raised when a source cannot be safely or reliably checked."""


class SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, expected_host: str) -> None:
        super().__init__()
        self.expected_host = expected_host

    def redirect_request(self, request, response, code, message, headers, new_url):
        if not _official_url(new_url, self.expected_host):
            raise MonitorError(f"Redirección fuera del dominio oficial permitido: {new_url}")
        return super().redirect_request(request, response, code, message, headers, new_url)


def _official_url(url: str, expected_host: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == expected_host
        and not parsed.username
        and not parsed.password
        and not port
    )


def _fetch(url: str, expected_host: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BBPlan-Official-Source-Monitor/1.0"},
    )
    try:
        opener = urllib.request.build_opener(SameHostRedirectHandler(expected_host))
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError, MonitorError) as error:
        raise MonitorError(f"Error consultando {url}: {error}") from error
    if len(body) > MAX_RESPONSE_BYTES:
        raise MonitorError(f"La respuesta de {url} supera el límite permitido.")
    return body


def _text(element: ET.Element, name: str) -> str:
    child = element.find(name)
    return " ".join("".join(child.itertext()).split()) if child is not None else ""


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self.skip_depth:
            normalized = " ".join(data.split())
            if normalized:
                self.parts.append(normalized)


def parse_html_page(body: bytes, source: dict[str, Any]) -> dict[str, dict[str, str]]:
    encoding = source.get("encoding", "utf-8")
    try:
        markup = body.decode(encoding)
    except (LookupError, UnicodeDecodeError) as error:
        raise MonitorError(f"No se pudo decodificar la página {source['id']}: {error}") from error
    parser = VisibleTextParser()
    parser.feed(markup)
    parser.close()

    text = " ".join(parser.parts)
    if len(text) < 100:
        raise MonitorError(
            f"La página {source['id']} no contiene texto suficiente; podría ser una página de error o bloqueo."
        )
    title = " ".join(" ".join(parser.title_parts).split()) or source["title"]
    fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        source["url"]: {
            "title": title,
            "link": source["url"],
            "published": "",
            "description": "Página oficial; la detección de cambios en el texto visible requiere revisión humana.",
            "fingerprint": fingerprint,
        }
    }


def parse_feed(body: bytes, source: dict[str, Any]) -> dict[str, dict[str, str]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise MonitorError(f"El RSS de {source['id']} no es XML válido: {error}") from error

    entries: dict[str, dict[str, str]] = {}
    elements = root.findall(".//item")
    if not elements:
        elements = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for element in elements:
        title = _text(element, "title")
        link = _text(element, "link")
        if not link:
            link_element = element.find("{http://www.w3.org/2005/Atom}link")
            link = link_element.get("href", "") if link_element is not None else ""
        guid = _text(element, "guid") or _text(element, "{http://www.w3.org/2005/Atom}id")
        published = _text(element, "pubDate") or _text(
            element, "{http://www.w3.org/2005/Atom}published"
        )
        updated = _text(element, "{http://www.w3.org/2005/Atom}updated")
        description = _text(element, "description") or _text(
            element, "{http://www.w3.org/2005/Atom}summary"
        )
        key = guid or link
        if not key:
            raise MonitorError(f"Entrada sin identificador ni enlace en {source['id']}.")

        entry = {
            "title": title or "(sin título)",
            "link": link,
            "published": published or updated,
            "description": description[:1000],
        }
        serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        entry["fingerprint"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        entries[key] = entry

    if not entries:
        raise MonitorError(f"El feed de {source['id']} no contiene publicaciones.")
    return entries


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as error:
        raise MonitorError(f"No se pudo leer {path.name}: {error}") from error


def validate_source(source: Any, trusted_hosts: list[str]) -> None:
    if not isinstance(source, dict):
        raise MonitorError("Cada elemento de sources debe ser un objeto JSON.")
    required = ("id", "title", "authority", "url", "host", "coverage")
    if any(not isinstance(source.get(key), str) or not source[key].strip() for key in required):
        raise MonitorError("Cada fuente debe incluir id, título, organismo, URL, host y cobertura.")
    if source.get("format") not in {"rss", "html", "reference"}:
        raise MonitorError(f"Formato no soportado en {source['id']}: {source.get('format')!r}")
    if source["host"] not in trusted_hosts:
        raise MonitorError(f"Dominio no incluido en la lista de fuentes oficiales aprobadas: {source['host']}")
    if not _official_url(source["url"], source["host"]):
        raise MonitorError(f"URL no HTTPS o dominio no autorizado para {source['id']}.")
    if source.get("format") == "reference":
        if not source.get("monitoring_note"):
            raise MonitorError(f"La referencia manual {source['id']} debe explicar por qué no se monitoriza.")
        return


def check_sources(
    sources: list[dict[str, Any]],
    old_state: dict[str, Any],
    trusted_hosts: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    new_state: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for source in sources:
        source_id = source.get("id", "(fuente sin id)") if isinstance(source, dict) else "(fuente inválida)"
        try:
            validate_source(source, trusted_hosts)
            if source["id"] in seen_ids:
                raise MonitorError(f"Identificador de fuente duplicado: {source['id']}")
            seen_ids.add(source["id"])
            if source["format"] == "reference":
                continue

            body = _fetch(source["url"], source["host"])
            entries = (
                parse_feed(body, source)
                if source["format"] == "rss"
                else parse_html_page(body, source)
            )
            previous = old_state.get(source["id"])
            if previous is not None and not isinstance(previous, dict):
                raise MonitorError(f"Línea base inválida para la fuente {source['id']}.")
            if previous is not None:
                for key, entry in entries.items():
                    old_entry = previous.get("entries", {}).get(key)
                    if old_entry is None:
                        changes.append({"source": source, "entry": entry, "kind": "new"})
                    elif old_entry.get("fingerprint") != entry["fingerprint"]:
                        changes.append({"source": source, "entry": entry, "kind": "updated"})

            new_state[source["id"]] = {
                "url": source["url"],
                "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "entries": {
                    key: {"fingerprint": entry["fingerprint"], "title": entry["title"]}
                    for key, entry in entries.items()
                },
            }
        except MonitorError as error:
            errors.append(f"{source_id}: {error}")
    return new_state, changes, errors


def _safe_markdown(value: str) -> str:
    return html.escape(value, quote=False).replace("|", "\\|").replace("`", "\\`")


def make_report(
    sources: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    first_run: bool,
    errors: list[str] | None = None,
    coverage_matrix: list[dict[str, Any]] | None = None,
) -> str:
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    lines = [
        "# Revisión de publicaciones oficiales",
        "",
        f"Comprobación: {now}",
        "",
        "> Este informe detecta nuevas entradas en feeds y cambios de texto en páginas oficiales. "
        "Los cambios pueden ser editoriales o técnicos: no interpreta su efecto legal, no "
        "actualiza las reglas de la web y no garantiza un inventario exhaustivo. Revisión humana obligatoria.",
        "",
    ]
    if first_run:
        lines.extend(
            [
                "## Línea base inicial",
                "",
                "Se creó la línea base de las fuentes monitorizadas. Las publicaciones y páginas "
                "ya presentes no se notifican como novedades; este primer registro no acredita que "
                "las reglas existentes estén vigentes.",
                "",
            ]
        )
    if changes:
        lines.extend(["## Novedades para revisar", ""])
        for change in changes:
            source = change["source"]
            entry = change["entry"]
            label = "Publicación nueva" if change["kind"] == "new" else "Publicación modificada"
            link = (
                entry["link"]
                if _official_url(entry["link"], source["host"])
                else "(enlace no incluido: dominio distinto del feed oficial)"
            )
            lines.extend(
                [
                    f"### {label}: {_safe_markdown(source['title'])}",
                    "",
                    f"- Organismo: {_safe_markdown(source['authority'])}",
                    f"- Publicación: {_safe_markdown(entry['title'])}",
                    f"- Fecha publicada en el feed: {_safe_markdown(entry['published'] or 'no indicada')}",
                    f"- Enlace: {link}",
                    f"- Cobertura y límites de esta fuente: {_safe_markdown(source['coverage'])}",
                    "",
                ]
            )
    elif not first_run:
        lines.extend(["No se detectaron entradas nuevas ni cambios en las fuentes consultadas.", ""])

    lines.extend(["## Fuentes monitorizadas", ""])
    for source in sources:
        if source.get("format") == "reference":
            continue
        lines.append(
            f"- [{_safe_markdown(source['title'])}]({source['url']}) "
            f"({_safe_markdown(source['authority'])}, {_safe_markdown(source.get('territory', ''))}): "
            f"{_safe_markdown(source['coverage'])}"
        )
    references = [source for source in sources if source.get("format") == "reference"]
    if references:
        lines.extend(["", "## Referencias oficiales pendientes de monitorización", ""])
        for source in references:
            lines.append(
                f"- [{_safe_markdown(source['title'])}]({source['url']}) "
                f"({_safe_markdown(source['authority'])}): "
                f"{_safe_markdown(source['monitoring_note'])}"
            )
    if coverage_matrix:
        lines.extend(["", "## Matriz de cobertura", ""])
        for item in coverage_matrix:
            source_titles = [
                source["title"]
                for source in sources
                if source["id"] in item.get("source_ids", [])
            ]
            lines.extend(
                [
                    f"- **{_safe_markdown(item['category'])}** — "
                    f"{_safe_markdown(item['status'])}. "
                    f"Fuentes: {_safe_markdown(', '.join(source_titles) or 'ninguna')}. "
                    f"Pendiente: {_safe_markdown(item['gap'])}"
                ]
            )
    if errors:
        lines.extend(["", "## Errores de consulta", ""])
        lines.extend(f"- {_safe_markdown(error)}" for error in errors)
    lines.extend(
        [
            "",
            "## Cobertura pendiente",
            "",
            "Los RSS de boletines no clasifican automáticamente las disposiciones pertinentes. "
            "Las páginas HTML se comparan por texto visible, lo que puede producir alertas por "
            "cambios editoriales o de diseño. Este monitor no valida importes, elegibilidad, "
            "fechas, semanas de permisos ni la exhaustividad de procesos.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    sources: list[dict[str, Any]] = []
    coverage_matrix: list[dict[str, Any]] = []
    first_run = False
    try:
        config = load_json(SOURCES_FILE, {})
        if not isinstance(config, dict):
            raise MonitorError("fuentes_oficiales.json debe contener un objeto JSON.")
        sources = config.get("sources")
        coverage_matrix = config.get("coverage_matrix", [])
        trusted_hosts = config.get("trusted_hosts")
        if not isinstance(sources, list) or not sources:
            raise MonitorError("fuentes_oficiales.json debe contener una lista sources no vacía.")
        if not isinstance(coverage_matrix, list):
            raise MonitorError("coverage_matrix debe ser una lista.")
        if not isinstance(trusted_hosts, list) or any(
            not isinstance(host, str) or not host for host in trusted_hosts
        ):
            raise MonitorError("fuentes_oficiales.json debe definir trusted_hosts.")

        old_state = load_json(STATE_FILE, {})
        if not isinstance(old_state, dict):
            raise MonitorError(f"{STATE_FILE.name} debe contener un objeto JSON.")
        is_initial_baseline = not old_state
        new_state, changes, errors = check_sources(sources, old_state, trusted_hosts)
        first_run = is_initial_baseline
        report = make_report(sources, changes, first_run, errors, coverage_matrix)
        if errors:
            REPORT_FILE.write_text(report, encoding="utf-8")
            print(report)
            print("Error: algunas fuentes no pudieron consultarse.", file=sys.stderr)
            return 1
        STATE_FILE.write_text(
            json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        REPORT_FILE.write_text(report, encoding="utf-8")
        if output_path := os.environ.get("GITHUB_OUTPUT"):
            with Path(output_path).open("a", encoding="utf-8") as output:
                output.write(f"changes={'true' if changes and not first_run else 'false'}\n")
        print(report)
        return 0
    except MonitorError as error:
        report = make_report(
            sources,
            [],
            not STATE_FILE.exists(),
            [str(error)],
            coverage_matrix,
        )
        REPORT_FILE.write_text(report, encoding="utf-8")
        print(report)
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
