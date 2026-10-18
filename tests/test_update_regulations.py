import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_regulations


class OfficialSourceMonitorTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "id": "boe",
            "title": "BOE",
            "authority": "Boletín Oficial del Estado",
            "url": "https://www.boe.es/rss.xml",
            "host": "www.boe.es",
            "format": "rss",
            "coverage": "Feed oficial de prueba.",
        }
        self.feed = b"""<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0"><channel><item>
          <title>Norma de prueba</title>
          <link>https://www.boe.es/diario_boe/txt.php?id=BOE-A-1</link>
          <guid>BOE-A-1</guid><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
        </item></channel></rss>"""
        self.trusted_hosts = ["www.boe.es"]

    def test_feed_parser_extracts_official_publication(self):
        entries = update_regulations.parse_feed(self.feed, self.source)
        self.assertEqual(list(entries), ["BOE-A-1"])
        self.assertEqual(entries["BOE-A-1"]["title"], "Norma de prueba")

    def test_entry_after_initial_baseline_is_reported_as_new(self):
        with patch("update_regulations._fetch", return_value=self.feed):
            state, changes, errors = update_regulations.check_sources(
                [self.source], {"boe": {"entries": {}}}, self.trusted_hosts
            )
        self.assertIn("boe", state)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "new")
        self.assertEqual(errors, [])

    def test_unchanged_entries_are_not_reported_again(self):
        with patch("update_regulations._fetch", return_value=self.feed):
            state, _, errors = update_regulations.check_sources(
                [self.source], {}, self.trusted_hosts
            )
            _, changes, errors = update_regulations.check_sources(
                [self.source], state, self.trusted_hosts
            )
        self.assertEqual(changes, [])
        self.assertEqual(errors, [])

    def test_modified_entry_is_reported(self):
        changed_feed = self.feed.replace(b"Norma de prueba", b"Norma actualizada")
        with patch("update_regulations._fetch", return_value=self.feed):
            state, _, _ = update_regulations.check_sources(
                [self.source], {}, self.trusted_hosts
            )
        with patch("update_regulations._fetch", return_value=changed_feed):
            _, changes, errors = update_regulations.check_sources(
                [self.source], state, self.trusted_hosts
            )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "updated")
        self.assertEqual(errors, [])

    def test_non_official_or_insecure_source_is_rejected(self):
        source = {**self.source, "url": "http://www.boe.es/rss.xml"}
        with self.assertRaises(update_regulations.MonitorError):
            update_regulations.validate_source(source, self.trusted_hosts)
        source = {**self.source, "host": "example.com", "url": "https://example.com/feed"}
        with self.assertRaises(update_regulations.MonitorError):
            update_regulations.validate_source(source, self.trusted_hosts)

    def test_empty_or_malformed_feed_fails_explicitly(self):
        with self.assertRaises(update_regulations.MonitorError):
            update_regulations.parse_feed(b"<rss><channel /></rss>", self.source)
        with self.assertRaises(update_regulations.MonitorError):
            update_regulations.parse_feed(b"not xml", self.source)

    def test_html_page_text_changes_are_detected(self):
        source = {
            **self.source,
            "id": "official-page",
            "url": "https://www.boe.es/page.html",
            "format": "html",
        }
        original = b"<html><head><title>Ayuda</title><script>dynamic()</script></head><body><main>" + b"Texto oficial. " * 20 + b"</main></body></html>"
        updated = original.replace(b"Texto oficial", b"Contenido nuevo")
        with patch("update_regulations._fetch", return_value=original):
            state, _, errors = update_regulations.check_sources(
                [source], {}, self.trusted_hosts
            )
        self.assertEqual(errors, [])
        with patch("update_regulations._fetch", return_value=updated):
            _, changes, errors = update_regulations.check_sources(
                [source], state, self.trusted_hosts
            )
        self.assertEqual(errors, [])
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "updated")

    def test_html_page_baseline_survives_url_change(self):
        source = {
            **self.source,
            "id": "official-page",
            "url": "https://www.boe.es/current-page.html?q=/current-page",
            "format": "html",
        }
        body = (
            b"<html><head><title>Ayuda</title></head><body><main>"
            + b"Texto oficial. " * 20
            + b"</main></body></html>"
        )
        old_entry = update_regulations.parse_html_page(
            body,
            {**source, "url": "https://www.boe.es/old-page.html"},
        )["official-page"]
        old_state = {
            "official-page": {
                "entries": {
                    "https://www.boe.es/old-page.html": {
                        "fingerprint": old_entry["fingerprint"],
                        "title": old_entry["title"],
                    }
                }
            }
        }
        with patch("update_regulations._fetch", return_value=body):
            _, changes, errors = update_regulations.check_sources(
                [source], old_state, self.trusted_hosts
            )

        self.assertEqual(errors, [])
        self.assertEqual(changes, [])

    def test_manual_reference_is_listed_but_not_fetched(self):
        source = {
            **self.source,
            "format": "reference",
            "monitoring_note": "HTTP 403",
        }
        with patch("update_regulations._fetch") as fetch:
            state, changes, errors = update_regulations.check_sources(
                [source], {}, self.trusted_hosts
            )
        fetch.assert_not_called()
        self.assertEqual(state, {})
        self.assertEqual(changes, [])
        self.assertEqual(errors, [])

    def test_manual_reference_must_be_official_https(self):
        source = {
            **self.source,
            "format": "reference",
            "monitoring_note": "No hay feed validado.",
            "url": "http://www.boe.es/",
        }
        with self.assertRaises(update_regulations.MonitorError):
            update_regulations.validate_source(source, self.trusted_hosts)

    def test_unavailable_source_keeps_last_good_baseline_and_reports_error(self):
        previous_entries = {
            "old-guid": {"fingerprint": "known-fingerprint", "title": "Last known title"}
        }
        previous_state = {
            "boe": {
                "url": self.source["url"],
                "checked_at": "2026-10-01T05:17:00+00:00",
                "last_successful_check": "2026-10-01T05:17:00+00:00",
                "status": "ok",
                "entries": previous_entries,
            }
        }
        with patch(
            "update_regulations._fetch",
            side_effect=update_regulations.MonitorError("HTTP Error 404: Not Found"),
        ):
            state, changes, errors = update_regulations.check_sources(
                [self.source], previous_state, self.trusted_hosts
            )

        self.assertEqual(changes, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(state["boe"]["status"], "error")
        self.assertEqual(state["boe"]["entries"], previous_entries)
        self.assertEqual(
            state["boe"]["last_successful_check"],
            "2026-10-01T05:17:00+00:00",
        )

    def test_unavailable_first_run_source_is_reported_without_fabricating_baseline(self):
        with patch(
            "update_regulations._fetch",
            side_effect=update_regulations.MonitorError("HTTP Error 404: Not Found"),
        ):
            state, changes, errors = update_regulations.check_sources(
                [self.source], {}, self.trusted_hosts
            )

        self.assertEqual(changes, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(state["boe"]["entries"], {})
        self.assertIsNone(state["boe"]["last_successful_check"])

    def test_main_succeeds_and_writes_error_output_for_unavailable_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sources_path = temp_path / "fuentes_oficiales.json"
            state_path = temp_path / "normative_sources_state.json"
            report_path = temp_path / "monitor_report.md"
            output_path = temp_path / "github_output.txt"
            old_entries = {
                "BOE-A-old": {"fingerprint": "old-hash", "title": "Last good entry"}
            }
            sources_path.write_text(
                json.dumps(
                    {
                        "sources": [self.source],
                        "trusted_hosts": self.trusted_hosts,
                        "coverage_matrix": [],
                    }
                ),
                encoding="utf-8",
            )
            state_path.write_text(
                json.dumps(
                    {
                        "boe": {
                            "checked_at": "2026-10-01T00:00:00+00:00",
                            "status": "ok",
                            "entries": old_entries,
                        }
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(update_regulations, "SOURCES_FILE", sources_path),
                patch.object(update_regulations, "STATE_FILE", state_path),
                patch.object(update_regulations, "REPORT_FILE", report_path),
                patch(
                    "update_regulations._fetch",
                    side_effect=update_regulations.MonitorError("HTTP Error 404: Not Found"),
                ),
                patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path)}),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = update_regulations.main()

            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            outputs = output_path.read_text(encoding="utf-8")
            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        self.assertIn("source_errors=true", outputs)
        self.assertEqual(saved_state["boe"]["status"], "error")
        self.assertEqual(saved_state["boe"]["entries"], old_entries)
        self.assertIn("HTTP Error 404", report)


if __name__ == "__main__":
    unittest.main()
