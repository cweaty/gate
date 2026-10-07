import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vpngate


class OutputTests(unittest.TestCase):
    def run_pipeline(self, output_dir, success):
        rows = [{
            "host": "vpn12345", "ip": "192.0.2.1", "country_long": "Japan",
            "country_short": "JP", "config_b64": base64.b64encode(
                b"proto tcp\nremote 192.0.2.1 443\n"
            ).decode(),
        }]
        results = [{
            "host": "vpn12345.opengw.net", "port": 443, "ip": "192.0.2.1",
            "country": "Japan", "country_code": "JP", "success": success,
            "residential": "residential", "latency_ms": 10,
        }]
        with patch.object(vpngate.requests, "Session"), \
                patch.object(vpngate, "fetch_vpngate", return_value=(rows, "fixture")), \
                patch.object(vpngate, "check_all", return_value=results), \
                patch.object(vpngate, "PUBLIC_DIR", str(output_dir)), \
                patch.object(vpngate, "log"):
            vpngate.main()

    def test_zero_success_does_not_write_outputs(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory(
                dir=Path(vpngate.REPO_DIR).parent
            ) as temp_dir:
                output_dir = Path(temp_dir) / "public"
                if existing:
                    output_dir.mkdir()
                    for name in ("data.json", "index.html", "nodes.txt"):
                        (output_dir / name).write_text("previous output", encoding="utf-8")
                with self.assertRaises(SystemExit) as raised:
                    self.run_pipeline(output_dir, success=False)
                self.assertEqual(raised.exception.code, 1)
                if existing:
                    for output in output_dir.iterdir():
                        self.assertEqual(output.read_text(encoding="utf-8"), "previous output")
                else:
                    self.assertFalse(output_dir.exists())

    def test_success_writes_outputs(self):
        with tempfile.TemporaryDirectory(dir=Path(vpngate.REPO_DIR).parent) as temp_dir:
            output_dir = Path(temp_dir) / "public"
            self.run_pipeline(output_dir, success=True)
            data = json.loads((output_dir / "data.json").read_text(encoding="utf-8"))
            self.assertEqual(data["stats"]["success"], 1)
            self.assertTrue((output_dir / "index.html").is_file())
            self.assertIn("$sstp://vpn:vpn@vpn12345.opengw.net:443",
                          (output_dir / "nodes.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
