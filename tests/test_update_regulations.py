import unittest
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


if __name__ == "__main__":
    unittest.main()
