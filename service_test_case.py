import requests
from threading import Event
from nio import Block
from nio.block.context import BlockContext
from nio.modules.communication.publisher import Publisher
from nio.modules.communication.subscriber import Subscriber
from nio.testing.test_case import NIOTestCase
from nio.router.context import RouterContext
from niocore.core.loader.discover import Discover
from service_tests.router import ServiceTestRouter


class NioServiceTestCase(NIOTestCase):

    service_name = None

    def __init__(self, methodName='runTests'):
        super().__init__(methodName)
        self._blocks = {}
        self._router = ServiceTestRouter()
        # Subscribe to publishers in the service
        self._subscribers = {}
        # Capture published signals for assertions
        self.published_signals = []
        # Set an event when those publishers publish signals
        self._publisher_event = Event()
        # Allow tests to publish signals to any subscriber
        self._publishers = {}

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
        # Init publishers and subscribers for tests
        self._setup_pubsub()

    def tearDown(self):
        super().tearDown()
        # Tear down publishers and subscribers for tests
        self._teardown_pubsub()
        # Stop blocks
        for block in self._blocks:
            self._blocks[block].stop()

    def publisher_topics(self):
        """Topics this service publishes to"""
        return []

    def subscriber_topics(self):
        """Topics this service subscribes to"""
        return []

    def _setup_pubsub(self):
        # Supscribe to published signals
        for publisher_topic in self.publisher_topics():
            self._subscribers[str(publisher_topic)] = \
                    Subscriber(self._published_signals, **publisher_topic)
        for subscriber in self._subscribers:
            self._subscribers[subscriber].open()
        # Allow tests to publish to subscribers in service
        for subscriber_topic in self.subscriber_topics():
            self._publishers[str(subscriber_topic)] = \
                    Publisher(**subscriber_topic)
        for publisher in self._publishers:
            self._publishers[publisher].open()

    def _teardown_pubsub(self):
        self.published_signals = []
        for subscriber in self._subscribers:
            self._subscribers[subscriber].close()
        for publisher in self._publishers:
            self._publishers[publisher].close()
        self._publisher_event = Event()

    def publish_signals(self, topic, signals):
        self._publishers[topic].send(signals)

    def _published_signals(self, signals):
        # Save published signals for assertions
        self.published_signals.extend(signals)
        self._publisher_event.set()
        self._publisher_event.clear()

    def override_block_configs(self):
        """Optionally override block config for the tests"""
        return {}

    def _override_block_config(self, block_config):
        new_block_config = self.override_block_configs().get(
            block_config["name"], block_config)
        new_block_config["name"] = block_config["name"]
        return new_block_config

    def wait_for_published_signals(self, count=0, timeout=1):
        """Wait for the specified number of signals to be published

        If no count is specified, then wait for the next signals to be
        published. If no signals are published before the timeout, then fail
        the test.

        Either returns after successfully waiting or fails an assertion
        """
        if not count:
            # Wait for next publisher event
            return self._publisher_event.wait(timeout)
        else:
            # Wait for specified number of signals
            while(count > len(self.published_signals)):
                return self._publisher_event.wait(timeout)
