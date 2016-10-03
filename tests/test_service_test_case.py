from unittest.mock import MagicMock
from ..service_test_case import NioServiceTestCase

class TestServiceTestCase(NioServiceTestCase):

    @classmethod
    def setUpClass(cls):
        cls.block_configs = []
        cls.service_config = {}

    def setUp(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

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
