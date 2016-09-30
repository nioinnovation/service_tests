import os
import re
import requests
from threading import Event
from nio import Block
from nio.block.context import BlockContext
from nio.modules.communication.publisher import Publisher
from nio.modules.communication.subscriber import Subscriber
from nio.modules.context import ModuleContext
from nio.testing.test_case import NIOTestCase
from nio.router.context import RouterContext
from niocore.core.loader.discover import Discover
from service_tests.router import ServiceTestRouter
from service_tests.module_persistence_file.module import FilePersistenceModule
from service_tests.module_persistence_file.persistence import Persistence


class NioServiceTestCase(NIOTestCase):
    """Base test case for n.io services

    To use:
        * Override class variable `service_name`.
        * If testing by publishing to subscriber, override `subscriber_topics`.
            Publish this signals with `publish_signals(topic, signals)`.
        * If asserting against publised signals, override `publisher_topics`
            Get published signals with `published_signals`.
        * If you need to change block config for a test, override
            `override_block_configs`
        * Use `wait_for_published_signals(self, count=0, timeout=1)` instead
            of sleep
        * Set n.io environement variables with `env_vars`.
    """

    service_name = None
    cfg_dir = "{}/{}/".format(os.path.dirname(__file__), "etc")

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

    def publisher_topics(self):
        """Topics this service publishes to"""
        return []

    def subscriber_topics(self):
        """Topics this service subscribes to"""
        return []

    def publish_signals(self, topic, signals):
        self._publishers[topic].send(signals)

    def override_block_configs(self):
        """Optionally override block config for the tests"""
        return {}

    def env_vars(self):
        """Optionally override to set environment variable values"""
        return {}

    def setUp(self):
        super().setUp()
        persistence = Persistence()
        self.block_configs = persistence.load_collection("blocks")
        self.service_configs = persistence.load_collection("services")
        self.service_config = self.service_configs.get(self.service_name, {})
        self._setup_blocks()
        self._setup_pubsub()

    def get_test_modules(self):
        return {'settings', 'scheduler', 'persistence', 'communication'}

    def get_context(self, module_name, module):
        if module_name == "persistence":
            context = ModuleContext()
            context.root_folder = self.cfg_dir
            context.root_id = ''
            context.format = Persistence.Format.json.value
            return context
        else:
            return super().get_context(module_name, module)

    def get_module(self, module_name):
        """ Override to use the file persistence """
        if module_name == "persistence":
            return FilePersistenceModule()
        else:
            return super().get_module(module_name)

    def _setup_blocks(self):
        # Instantiate and configure blocks
        blocks = Discover.discover_classes('blocks', Block)
        service_block_names = [service_block["name"] for service_block in \
                               self.service_config.get("execution", [])]
        service_block_mappings = {}
        for mapping in self.service_config.get("mappings", []):
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
            block_config = self._replace_env_vars(block_config)
            block.configure(BlockContext(
                self._router, block_config, 'TestSuite', ''))
            self._blocks[service_block_name] = block
        # Configure router
        self._router.configure(RouterContext(
            execution=self.service_config.get("execution", []),
            blocks=self._blocks))
        # Start blocks
        for block in self._blocks:
            self._blocks[block].start()

    def _replace_env_vars(self, config):
        """Return config with environment vatriables swapped out"""
        for var in self.env_vars():
            config = \
                self._replace_env_var(config, var, self.env_vars()[var])
        return config

    def _replace_env_var(self, config, name, value):
        for property in config:
            if isinstance(config[property], str):
                config[property] = re.sub("\[\[" + name + "\]\]",
                                          str(value),
                                          config[property])
            elif isinstance(config[property], dict):
                self._replace_env_var(config[property], name, value)
            elif isinstance(config[property], list):
                new_list = []
                for item in config[property]:
                    if isinstance(item, str):
                        new_list.append(re.sub("\[\[" + name + "\]\]",
                                               str(value),
                                               item))
                    elif isinstance(item, dict):
                        new_list.append(
                                self._replace_env_var(item, name, value))
                config[property] = new_list
        return config

    def tearDown(self):
        super().tearDown()
        # Tear down publishers and subscribers for tests
        self._teardown_pubsub()
        # Stop blocks
        for block in self._blocks:
            self._blocks[block].stop()

    def _setup_pubsub(self):
        # Supscribe to published signals
        for publisher_topic in self.publisher_topics():
            self._subscribers[publisher_topic] = \
                    Subscriber(self._published_signals, topic=publisher_topic)
        for subscriber in self._subscribers:
            self._subscribers[subscriber].open()
        # Allow tests to publish to subscribers in service
        for subscriber_topic in self.subscriber_topics():
            self._publishers[subscriber_topic] = \
                    Publisher(topic=subscriber_topic)
        for publisher in self._publishers:
            self._publishers[publisher].open()

    def _teardown_pubsub(self):
        self.published_signals = []
        for subscriber in self._subscribers:
            self._subscribers[subscriber].close()
        for publisher in self._publishers:
            self._publishers[publisher].close()
        self._publisher_event = Event()

    def _published_signals(self, signals):
        # Save published signals for assertions
        self.published_signals.extend(signals)
        self._publisher_event.set()
        self._publisher_event.clear()

    def _override_block_config(self, block_config):
        new_block_config = self.override_block_configs().get(
            block_config["name"], block_config)
        for property in new_block_config:
            block_config[property] = new_block_config[property]
        return block_config

    def wait_for_published_signals(self, count=0, timeout=1):
        """Wait for the specified number of signals to be published

        If no count is specified, then wait for the next signals to be
        published. If no signals are published before the timeout, then fail
        the test.

        Either returns after successfully waiting or fails an assertion
        """
        if not count:
            # Wait for next publisher event
            self._publisher_event.wait(timeout)
        else:
            # Wait for specified number of signals
            while(count > len(self.published_signals)):
                if not self._publisher_event.wait(timeout):
                    return
