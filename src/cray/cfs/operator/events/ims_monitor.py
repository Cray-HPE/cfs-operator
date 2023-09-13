#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Functions for handling orphaned IMS jobs from failed image customization.
"""
import logging
import threading
import time

import cray.cfs.operator.cfs.sessions as cfs_sessions
from cray.cfs.utils.clients.ims.jobs import get_jobs as get_ims_jobs
from cray.cfs.utils.clients.ims.jobs import delete_job as delete_ims_job

LOGGER = logging.getLogger('cray.cfs.operator.events.ims_monitor')


class IMSJobMonitor:
    def run(self):
        threading.Thread(target=self._run).start()

    def _run(self):  # pragma: no cover
        while True:
            try:
                jobs = self._get_running_ims_jobs()
                if jobs:
                    self._cleanup_orphaned_ims_jobs(jobs)
            except Exception as e:
                LOGGER.warning('Exception during IMS session cleanup: {}'.format(e))
            time.sleep(60)

    @staticmethod
    def _get_running_ims_jobs():
        jobs = get_ims_jobs()
        return [job["id"] for job in jobs if job.get("status") not in ["success", "error"]]

    @staticmethod
    def _cleanup_orphaned_ims_jobs(ims_jobs):
        error = None
        for session in cfs_sessions.iter_sessions(parameters={"status": "complete"}):
            try:
                ims_job_id = session.get("status", {}).get("session", {}).get("ims_job")
                if ims_job_id and ims_job_id in ims_jobs:
                    delete_ims_job(ims_job_id)
            except Exception as e:
                error = e
        if error:
            # This makes an attempt for every job that needs deleting before raising an exception
            # In the event of multiple exceptions only the last will be raised and logged
            raise error
