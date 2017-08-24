from nio.modules.module import Module
from nio.modules.scheduler.job import Job


class SchedulerModule(Module):

    def proxy_job_class(self, job_class):
        Job.proxy(job_class)

    def finalize(self):
        Job.unproxy()
        super().finalize()

    def get_module_order(self):
        return 5

    def get_module_type(self):
        return "scheduler"
