import subprocess
import time
import logging
import multiprocessing.pool


class IPMI:
    SINGLE_THREADED_WORKER_SIZE = 1

    def __init__(self, hostname, username, password):
        self._hostname = hostname
        self._username = username
        self._password = password
        self._worker = multiprocessing.pool.ThreadPool(IPMI.SINGLE_THREADED_WORKER_SIZE)

    def off(self):
        self._worker.apply_async(self._powerCommand, args=("off",))

    def powerCycle(self):
        self._worker.apply_async(self._powerCycle)

    def _powerCycle(self):
        self._powerCommand("off")
        self._powerCommand("on")

    def _excuteIPMITool(self, cmdArray, retryCount=10):
        cmdLine = ['ipmitool', '-H', str(self._hostname), "-U", self._username,
                   "-P", self._password] + cmdArray
        tryNumber = 0
        while True:
            try:
                return subprocess.check_output(cmdLine, stderr=subprocess.STDOUT, close_fds=True)
            except subprocess.CalledProcessError as e:
                if tryNumber >= retryCount:
                    logging.error("Output: %(output)s", dict(output=e.output))
                    raise
                tryNumber += 1
                time.sleep(0.1)

    def _forceBootFrom(self, boot):
        ALLOWED_BOOT_OPTIONS = ['pxe']
        if boot not in ALLOWED_BOOT_OPTIONS:
            raise Exception("Boot option %s is not allowed" % boot)
        bootenvCommand = ['chassis', 'bootdev', boot]
        bootenvCommand = bootenvCommand + ['options=persistent']
        self._excuteIPMITool(bootenvCommand, retryCount=1)

    def forceBootFrom(self, boot):
        self._worker.apply_async(self._forceBootFrom, kwds={'boot': boot})

    def _powerCommand(self, command):
        self._excuteIPMITool(['power', command], retryCount=10)
