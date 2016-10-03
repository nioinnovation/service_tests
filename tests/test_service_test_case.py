from unittest.mock import MagicMock
from service_tests.service_test_case import NioServiceTestCase

class TestServiceTestCase(NioServiceTestCase):

    def test_block_and_service_configs_are_loaded_from_files(self):
        """Block and service config files are loaded from etc directory"""
        self.assertGreater(len(self.block_configs), 0)
        self.assertGreater(len(self.service_configs), 0)

    def test_replace_env_vars(self):
        """Configuration with variables gets replaced with value"""
        self.env_vars = MagicMock(return_value={
            "VAR": "var",
            "VAR_1": 1,
            "VAR_2": "2",
        })
        self.assertDictEqual(
            self._replace_env_vars({
                "no_var": "no variable",
                "with_var": "[[VAR_1]]",
                "with_var_and_text": "pre[[VAR_2]]post",
                "list": [
                    {"var": "[[VAR]]"},
                    {"var": "{{ [[VAR]] }}"},
                    "[[VAR]]",
                ],
                "dict": {
                    "var": "[[VAR]]",
                },
            }),
            {
                "no_var": "no variable",
                "with_var": "1",
                "with_var_and_text": "pre2post",
                "list": [
                    {"var": "var"},
                    {"var": "{{ var }}"},
                    "var",
                ],
                "dict": {
                    "var": "var",
                },
            }
        )
