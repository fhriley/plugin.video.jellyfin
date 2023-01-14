import os
import tempfile
import unittest

from lib.source.settings import Settings, load_settings_file


class TestSettings(unittest.TestCase):
    def test_load_settings_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = os.path.join(temp_dir, Settings.SETTINGS_FILE_NAME)
            settings = load_settings_file(settings_path)
            device_id = settings['device_id']

            settings = load_settings_file(settings_path)
            self.assertEqual(device_id, settings['device_id'])
