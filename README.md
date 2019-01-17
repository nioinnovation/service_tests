# nio service unit tests

Testing is a necessary part of designing a robust nio system. For self-managed instances, you can ensure your block or service configurations are performing correctly with the [Service Unit Test Framework](https://github.com/niolabs/service_tests).

Service unit tests are written in Python code and make use of the [Python unittest module](https://docs.python.org/3/library/unittest.html).

---

## Getting started

If you installed the nio [project template](https://github.com/niolabs/project_template) using the nio CLI or from the repository, then your test files are all set up in your project directory. If not, complete the following steps:

Clone this repo into your nio project directory as a submodule
```
git submodule add https://github.com/niolabs/service_tests.git
```
Then create a **tests** directory for your service unit tests.
```
mkdir tests && touch tests/__init__.py
```
Example project file structure:

```
- nio.conf
- etc/
- blocks/
- tests/
  - __init__.py
- service_tests/
  - service_test_case.py
```

Install _jsonschema_ for publisher/subscriber topic validation.

```
pip3 install jsonschema
```

---

## Setting up your test class

Generally speaking, you will have a service test file (and class) for each service. You can use the following example as a starting point for your service unit test files:

```python
from nio.signal.base import Signal
from .service_test_case import NioServiceTestCase


class TestExampleService(NioServiceTestCase):

    service_name = "ExampleService"

    def subscriber_topics(self):
        """Topics this service subscribes to"""
        return ['topic1', 'topic2']

    def publisher_topics(self):
        """Topics this service publishes to"""
        return ['topic3']

    def env_vars(self):
        """Environment variables"""
        return {
            "TEST_VARIABLE": "test variable"
        }

    def test_service(self):
        topic1 = self.subscriber_topics()[0]
        self.publish_signals(topic1, [Signal({
            "data": self.env_vars()["TEST_VARIABLE"]
        })])
        self.assert_num_signals_published(1)
        self.assert_signal_published({
            "data": "test variable"
        })
```

Each test class can only contain unit tests for one service. These unit tests are not meant for testing interaction between services. Testing interactions between services would be integration testing.

**Set `service_name` class attribute**<br>The very first thing to do is change the class attribute `service_name` from **ExampleService** to your service name. This is how the test will know which service and blocks to load and configure. You can use your service's name or ID for this variable.

**Override `subscriber_topics` and `publisher_topics`**<br>If the service has _Subscriber_ or _Publisher_ blocks, override these methods to return a list of the topic names in your service. This allows your tests to publish test signals to the subscribers and to assert against the published signals from the service.

**Add `env_vars`**<br>These service tests will not read from any of your project `.env` files so if you want to use some environment variables, override this method and have it return a dictionary that maps environment variable names to values.

---

## Kicking off tests

If your service has blocks that generate signals on their own (e.g., _Simulator_ blocks), then the service will already be running with signals when each test is entered. However, it's easier to test services when you have control over the created signals.

You can create a signal and send it from any block with:

```python
self.notify_signals(block_name, signals)
```
You can create a signal and publish it to a topic to notify from the matching _Subscriber_ block(s) with:

```python
self.publish_signals(topic, signals)
```

---

## Getting processed and published signals

Once a block processes a signal or the signal has been published from the service you can retrieve that signal.

To get the signals published on a certain topic in a service use:
```python
self.published_signals[topic]
```

Similarly, you can get the signals processed by a block by using `self.processed_signals` and the block ID. (Note that it must be the block ID, not the block name. See the section below on block IDs vs names in service tests.)

```python
self.processed_signals[block_id]
```

### Block names and block IDs

Blocks (and services) can have an optional name along with their ID. In most methods in the service test you can provide either a block's name or ID to reference a block. You can find a block's ID by opening the block edit modal in the System Designer.

If your service uses two of the same block config it is best to refer to the blocks by their IDs rather than their names in the tests. This prevents undefined behavior from selecting/targeting the wrong block.

If referencing a block in a dictionary (like `self.processed_signals`) you must use the block ID. The service test provides a helpful method to determine a block ID based on the name, `self.get_block_id(name)`. 

So, to get the processed signals for a block named `'blocky'` you would do this:
```python
self.processed_signals[self.get_block_id('blocky')]
```

## Making assertions about signals

Most service unit tests will be structured so that you publish or emit a signal from a block at the beginning of a service and then inspect the output at the end of the service. The easiest way to make these assertions is by checking which signals the service's _Publisher_ blocks have published.

You can assert that your service published a certain number of signals using the service's assertion helper method:
```python
# Make sure our service published 3 signals
self.assert_num_signals_published(3)
```

Or, for specific topics:
```python
# Make sure we published 3 signals on the mydata.value topic
self.assert_num_signals_published(3, 'mydata.value')
```

Instead of waiting for or depending on a service to publish signals, you can assert that a specific block has processed signals. This is useful if the termination of your service is not a publisher but some other kind of block like an API or database.
```python
# Make sure the MyBlock block has processed 3 signals
self.assert_num_signals_processed(3, 'MyBlock')
```

## Service Test Timing

nio services are real-time and asynchronous. The service test case framework alleviates some of the common challenges that come with testing complex applications like that.

Sometimes making assertions immediately after publishing a signal into a service or block causes the assertions to fail. That is because the signal hasn't propogated through the nio service by the time you make your assertion. Rather than adding sleep in your tests or including while loops that wait for conditions, you can use the service test helper methods to wait for things to happen before making your assertions. 

To wait until signals are published use the `wait_for_published_signals` method. This method will block until a number of signals have been published on the service.
```python
# Wait until a signal has been published on mydata.value before asserting, but no more than 3 seconds
self.wait_for_published_signals(1, timeout=3)
self.assert(my_assert_conditions)
```

Similarly, you can wait for blocks to process signals before proceeding in your test.
```python
# Wait until a signal has been processed by MyBlock before asserting, but no more than 3 seconds
self.wait_for_processed_signals(1, 'MyBlock', timeout=3)
self.assert(my_assert_conditions)
```

Most blocks also support the ability to fake time so you can jump ahead in time to check signals. For example, a _SignalTimeout_ block may be configured to emit a timeout signal after 10 seconds. Instead of making your test take 10 seconds, jump ahead in time with

```python
self._scheduler.jump_ahead(seconds=10)
```

---

## Customization

The service test base class allows for some customization about how your service runs

###  Custom block config

You can override a block's configuration by implementing the `override_block_configs` method in your test class. This method should return a dictionary where the keys are block names or IDs and the value is a dictionary of properties to change on the block. Note that the properties are merged in to the existing properties, not replaced.

For example, assume we have a simulator block configured to emit 1 signal every 30 mintues:
**my_sim_block.cfg**
```json
{
    "interval": {
        "days": 0,
        "microseconds": 0,
        "seconds": 1800
    },
    "name": "my_sim_block",
    "num_signals": 1,
    "total_signals": -1,
    "type": "CounterIntervalSimulator"
}
```

In our test, we can override the behavior of the block to emit a signal every 5 seconds instead by adding this method implementation to the block class:
```python
def override_block_configs(self):
    return {
        "my_sim_block": {
            "interval": {
                "days": 0,
                "microseconds": 0,
                "seconds": 5
            }
        }
    }
```

### Mocking Blocks

Sometimes you don't want a block to process a signal at all, or you want to make much richer assertions about the block's behavior. Rather than just changing a block's configuration, the service test class provides the ability to replace a running block with a Python `Mock` instance. This can be useful if your block makes remote API calls or connections that you don't want to occur when running tests.

To mock a block, return a dictionary with the key being the name/ID of the block in the `mock_blocks` method in your service test. This example will mock a block called `'send_tweets'` with a Python `Mock` instance.

```python
def mock_blocks(self):
    return {
        "send_tweets": Mock()
    }
```

You can also mock just a block's process signals function by providing a method as the value rather than a Mock instance. Doing this allows the block to configure and start like normal but allows you to control the `process_signals` method call in the test. This example will call the test's custom process signals method on the `'send_tweets'` block:
```python
def my_custom_process_signals(self, signals):
    print("The test processed {} signals".format(len(signals)))

def mock_blocks(self):
    return {
        "send_tweets": self.my_custom_process_signals
    }
```

### Custom Environment/User Defined Variables

Tests can use custom environment or user-defined variables by returning them in the `env_vars` method in your test class.

```python
def env_vars(self):
    return {
        "DATABASE_HOST": "localhost"
    }
```

### Custom Block Persistence

To simulate and test a service's behavior given specific block persistence values, return the desired initial persistence state in your service test's `override_block_persistence` method. This example has the `'counter_block'` block start off with a cumulative count of 10 rather than the default of 0.
```python
def override_block_persistence(self):
    return {
        'counter_block': {
            '_cumulative_count': { None: 10 }
        }
    }
```
*Note: the `{None: 10}` syntax is due to the way the Counter block processes counts with groups. It is essentially setting the count of the `None` group to 10. Look at block code or existing persistence files to figure out the right format for your use case*

---
## Assertions

The service test case base class comes with some handy assertion methods that can be used in your test cases.

### assert_num_signals_published

Make sure a certain number of signals was published by the service.

```python
def assert_num_signals_published(self,
    expected,  # int - the number of signals expected
)
```

**Example:**
```python
# Make sure 5 signals were published by the service
self.assert_num_signals_published(5)
```

### assert_num_signals_processed

Make sure a certain number of signals was processed by a particular block

```python
def assert_num_signals_processed(self,
    expected,  # int - the number of signals expected
    block_name,  # str - the name or ID of the block to assert against
    input_id=None,  # str - optional - the input ID of the block to check
)
```

**Example:**
```python
# Make sure our 'count' block received 5 signals
self.assert_num_signals_processed(5, 'count')
```

### assert_signal_published

Make sure that the service published a signal that looks like a given dictionary.

```python
def assert_signal_published(self,
    signal_dict,  # dict - The dictionary of what a signal should look like
)
```

**Example:**
```python
# Make sure our service published the right count signal
self.assert_signal_published({
    "count": 5,
    "group": "group"
})
```

---

## Asynchronous service tests

There is an option to run the service tests asynchronously by setting the class attribute `synchronous=False`.
This will run the service as it would on an actual nio instance. Because of this behavior, some waiting is required to make sure that signals get to their destination before doing assertions on them.

### Waiting for signals (asynchronous)

Wait for signals to be published with:

```python
# count: number of cumulative signals to wait for since the service started
# timeout: time in seconds to wait before returning, even if *count* has not been reached
wait_for_published_signals(count=0, timeout=1)
```

Another option is to wait for a block to process signals:

```python
wait_for_processed_signals(block, number, timeout)
```

---

## Subscriber/Publisher topic validation with _jsonschema_

You can also validate signals associated with _Publisher_ and _Subscriber_ blocks by putting a JSON-schema formatted JSON file called `topic_schema.json` in one of three locations: `project_name/tests`, `project_name/`, or one directory above `project_name/`. For more information, see <http://json-schema.org/> and <https://spacetelescope.github.io/understanding-json-schema/UnderstandingJSONSchema.pdf>.

Signals published to the specified topics will be validated according to the file specification.

For instance, this JSON schema will make sure that all signals published to the topic "test_topic" are dictionary objects with at least one property. All signals going into this topic are required to have a **test_attribute** attribute, which can be a string or integer. Any additional properties on the signal must be of type integer.

```python
{
  "test_topic": {
    "type": "object",
    "minProperties": 1,
    "properties": {
      "test_attribute": {"type": ["string", "integer"],
                         "minlength": 1}
    },
    "required": ["test_attribute"],
    "additionalProperties": {"type": "integer"}
  }
}
```

---

## Running the tests

Execute the service tests using a Python test runner from your project directory.
```python
py.test tests
```
