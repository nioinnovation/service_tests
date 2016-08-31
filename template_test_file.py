from threading import Event
from nio.modules.communication.subscriber import Subscriber
from nio.modules.communication.publisher import Publisher
from nio.signal.base import Signal
from service_tests.service_test_case import NioServiceTestCase


class TestExample(NioServiceTestCase):

    service_name = "Example"

    def subscriber_topics(self):
        """Topics this service subscribes to"""
        return [
            {"key": ["value"]}
        ]

    def test_service(self):
        subscriber_topic = str(self.subscriber_topics()[0])
        self.publish_signals(subscriber_topic, [Signal({"input": "signal"})])
        self.wait_for_published_signals(1)
        self.assertEqual(len(self.published_signals), 1)
        self.assertDictEqual(self.published_signals[-1].to_dict(), {
            "output": "signal"
        })
