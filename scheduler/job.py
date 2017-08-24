from .scheduler import Scheduler


class Job(object):

    def __init__(self, target, delta, repeatable, *args, **kwargs):
        self._job = Scheduler.schedule_task(
            target, delta, repeatable, *args, **kwargs)

    def cancel(self):
        Scheduler.unschedule(self._job)

    def jump_ahead(self, seconds):
        """ Jump the scheudler forward a certain number of seconds.

        This is useful in tests to simulate time passing for event-driven
        logic and temporal assertions.
        """
        Scheduler.jump_ahead(seconds)
