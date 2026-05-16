import json
import os
import tempfile
import unittest
from unittest import mock

import modules


class DBBootstrapTests(unittest.TestCase):
    def test_ensure_db_creates_expected_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "db.json")
            with mock.patch.object(modules, "DB_PATH", db_path):
                modules.ensure_db()
                self.assertTrue(os.path.exists(db_path))
                with open(db_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                self.assertIn("channel", payload)
                self.assertIn("videos", payload)
                self.assertEqual(payload["videos"], [])


if __name__ == "__main__":
    unittest.main()
