from threading import Event
from nio.modules.communication.subscriber import Subscriber
from nio.modules.communication.publisher import Publisher
from nio.signal.base import Signal
from tests.service_test_case import NioServiceTestCase


class TestExample(NioServiceTestCase):

    service_name = "Example"

    def __init__(self, methodName='runTests'):
        super().__init__(methodName)
        # Subscribe to a publisher
        self._subsciber = None
        # Set an event when that publisher sends signals
        self._publisher_event = Event()
        self.published_signals = []
        # Allow tests to publish signals to any subscriber
        self._publishers = {}
        # Time to wait for published signals
        self._publisher_wait_timeout = 1

    def setUp(self):
        super().setUp()
        # Supscribe to published signals
        topic = {"subscriber": ["one"]}
        self._subscriber = Subscriber(self._published_signals,
                                      matching_provider="",
                                      **topic)
        self._subscriber.open()
        # Allow tests to publish to subscribers in service
        self._publishers["publisher_one"] = Publisher(publisher=["one"])
        self._publishers["publisher_two"] = Publisher(publisher=["two"])
        for publisher in self._publishers:
            self._publishers[publisher].open()

    def tearDown(self):
        super().tearDown()
        self.published_signals = []
        self._subscriber.close()
        for publisher in self._publishers:
            self._publishers[publisher].close()
        self._publisher_event = Event()

    def _publish_signals(self, topic, signals):
        self._publishers[topic].send(signals)

    def _published_signals(self, signals):
        # Save published signals for assertions
        self.published_signals.extend(signals)
        self._publisher_event.set()
        self._publisher_event.clear()

    def wait_for_published_signals(self, count=0):
        """Wait for the specified number of signals to be published

        If no count is specified, then wait for the next signals to be
        published. If no signals are published before the timeout, then fail
        the test.

        Either returns after successfully waiting or fails an assertion
        """
        if not count:
            # Wait for next publisher event
            self.assertTrue(
                self._publisher_event.wait(self._publisher_wait_timeout))
        else:
            # Wait for specified number of signals
            while(count > len(self.published_signals)):
                self.assertTrue(
                    self._publisher_event.wait(self._publisher_wait_timeout))

    def test_service(self):
        self._publish_signals("publisher_one", [Signal({"input": "signal"})])
        self.wait_for_published_signals(1)
        self.assertEqual(len(self.published_signals), 1)
        self.assertTrue({"output": "signal"},
                        self.published_signals[-1].to_dict())
