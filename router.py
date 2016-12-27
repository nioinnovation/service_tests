from collections import defaultdict
from copy import deepcopy
from threading import Event

from nio.router.base import BlockRouter
from nio.util.threading.spawn import spawn


class ServiceTestRouter(BlockRouter):

    def __init__(self):
        super().__init__()
        self._execution = []
        self._blocks = {}
        self._processed_signals = defaultdict(list)

    def configure(self, context):
        self._execution = context.execution
        self._blocks = context.blocks
        self._setup_processed()

    def notify_signals(self, block, signals, output_id):
        from_block_name = block.name()
        all_receivers = [block["receivers"] for block in self._execution
                         if block["name"] == from_block_name][0]
        # If output_id isn't in receivers, then use default output
        receivers = all_receivers.get(
            output_id, all_receivers.get("__default_terminal_value", []))
        for receiver in receivers:
            receiver_name = receiver["name"]
            input_id = receiver["input"]
            to_block = self._blocks[receiver_name]
            print("{} -> {}".format(from_block_name, receiver_name))
            cloned_signals = deepcopy(signals)
            if input_id == "__default_terminal_value":
                # don't include input_id if it's default terminal
                spawn(to_block.process_signals, cloned_signals)
            else:
                spawn(to_block.process_signals, cloned_signals, input_id)

    def _processed_signals_set(self, block_name):
        self._blocks[block_name]._processed_event.set()
        self._blocks[block_name]._processed_event.clear()

    def _call_processed(self, process_signals, block_name):
        """function wrapper for calling a block's _processed_signals after
        its process_signals.
        """
        def process_wrapper(*args, **kwargs):
            process_signals(*args, **kwargs)
            self._processed_signals[block_name].extend(*args)
            self._processed_signals_set(block_name)
        return process_wrapper

    def _setup_processed(self):
        """wrap every block's (including mocked blocks) process_signals
        function with a custom one that calls _processed_signals upon exit.

        Also give every block it's own event for processed_signals.
        """
        for block_name, block in self._blocks.items():
            block.process_signals = self._call_processed(block.process_signals,
                                                         block_name)
            block._processed_event = Event()
