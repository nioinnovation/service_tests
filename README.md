# n.io Service Unit Tests

This is a testing framework for writting and running unit tests for n.io services.

## Getting started with the framework

Close this repo into your n.io project directory as a submodule and create a **tests** directory for you service unit tests. Example project file structure:

```
- nio.env
- nio.conf
- etc/
- blocks/
- **tests/**
  - **__init__.py**
- **service_tests/**
  - **service_test_case.py**
```


## Setting up your test class

Generally speaking, you will have a service test file (and class) for each service. As a starting point for your service unit test files, you can use *template_test_file.py*.

Each test class can only contain unit tests for one service. These unit tests are not meant for testing interaction between services. That would be intergration testing.

### *service_name* class attribute

The very first thing you need to do is set the class attribute *service_name* to your service name. This is how the test will know which service to load and configure blocks for.

### *subcriber_topics* and *pubisher_topics*

If the service has subscriber or publisher blocks, override these methods to return a list of those topic names. This allows your tests to publish test signals to the subscribers and to assert against the published signals from the service.

### *env_vars*

These service tests will not read from any of your project env files so if you want to use some, overred this method and have it return a dictionary that maps environment variable names to values.

## Kicking off tests

If your service has blocks that generate signals on their own (ex: simulator blocks), then the service will already be running with signals when each test is entered. But it's easier to test services where you can have control over the created signals. You can create a signal and have it be notified from any block. You can create a signal and publish it to be notified by matching subciber block(s).

Publish signals to subscriber blocks with:

```python
publish_signals(topic, signals)
```

Notify signals from any block with:

```python
notify_signals(block_name, signals, terminal="__default_terminal_value")
```

## Making assertions about signals

Most service unit tests will be structured in such a way that you publish or a notify a signal at a block at the beginning of a service and then inspect the output at the end of the service. The easiest way to make these assertions is by checking which signals the service's publishers have published.

Get published signals with:

```python
published_signals(signals)
```

## Waiting for signals

Instead of introducing sleeps or race conditions, wait for signals to be published with:

```python
# count: number of cumulative signals to wait for since the service started
# timeout: time in seconds to wait before returning, even if *count* has not been reached
wait_for_published_signals(count=0, timeout=1)
```

Most blocks also support the ability to fake time so you can jump ahead in time to check signals. For example, a SignalTimeout block may be configured to notify a timeout signal after 10 seconds. Instead of making your test take 10 seconds, jump ahead in time with:

```python
from nio.testing.modules.scheduler.scheduler import JumpAheadScheduler
JumpAheadScheduler.jump_ahead(10)
```
