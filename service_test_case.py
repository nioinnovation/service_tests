import requests
from nio import Block
from nio.block.context import BlockContext
from nio.testing.test_case import NIOTestCase
from nio.router.context import RouterContext
from niocore.core.loader.discover import Discover
from tests.router import ServiceTestRouter


class NioServiceTestCase(NIOTestCase):

    service_name = None

    def __init__(self, methodName='runTests'):
        super().__init__(methodName)
        self._blocks = {}
        self._router = ServiceTestRouter()

    def get_test_modules(self):
        return {'settings', 'scheduler', 'persistence', 'communication'}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block_configs = requests.get('http://127.0.0.1:8181/blocks',
                                         auth=('Admin', 'Admin')).json()
        cls.service_config = requests.get('http://127.0.0.1:8181/services/{}'
                                          .format(cls.service_name),
                                          auth=('Admin', 'Admin')).json()

    def setUp(self):
        super().setUp()
        # Instantiate and configure blocks
        blocks = Discover.discover_classes('blocks', Block)
        service_block_names = [service_block["name"] for service_block in \
                               self.service_config["execution"]]
        service_block_mappings = {}
        for mapping in self.service_config["mappings"]:
            service_block_mappings[mapping["name"]] = mapping["mapping"]
        for service_block_name in service_block_names:
            # get mapping name or leave original name
            mapping_name = service_block_mappings.get(service_block_name,
                                                      service_block_name)
            block_config = self.block_configs.get(mapping_name)
            if not block_config:
                # skip blocks that don't have a config - this is a problem
                continue
            # use mapping name for block
            block_config["name"] = service_block_name
            # instantiate the block
            block = [block for block in blocks if \
                     block.__name__ == block_config["type"]][0]()
            block_config = self._override_block_config(block_config)
            block.configure(BlockContext(
                self._router, block_config, 'TestSuite', ''))
            self._blocks[service_block_name] = block
        # Configure router
        self._router.configure(RouterContext(
            execution=self.service_config["execution"],
            blocks=self._blocks))
        # Start blocks
        for block in self._blocks:
            self._blocks[block].start()

    def tearDown(self):
        super().tearDown()
        # Stop blocks
        for block in self._blocks:
            self._blocks[block].stop()

    def override_block_configs(self):
        """Optionally override block config for the tests"""
        return {}

    def _override_block_config(self, block_config):
        new_block_config = self.override_block_configs().get(
            block_config["name"], block_config)
        new_block_config["name"] = block_config["name"]
        return new_block_config
