from collections import defaultdict
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

    def notify_signals(self, block, signals, output_id):
        from_block_name = block.name()
        all_receivers = [block["receivers"] for block in self._execution \
                     if block["name"] == from_block_name][0]
        # If output_id isn't in receivers, then use default output
        receivers = all_receivers.get(
            output_id, all_receivers.get("__default_terminal_value", []))
        for receiver in receivers:
            receiver_name  = receiver["name"]
            input_id  = receiver["input"]
            to_block = self._blocks[receiver_name]
            print("{} -> {}".format(from_block_name, receiver_name))
            if input_id == "__default_terminal_value":
                # don't include input_id if it's default terminal
                spawn(to_block.process_signals, signals)
            else:
                spawn(to_block.process_signals, signals, input_id)
            self._processed_signals[to_block.name()].extend(signals)
