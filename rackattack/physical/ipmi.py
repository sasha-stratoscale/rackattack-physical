import subprocess
import time
import logging
import multiprocessing.pool


class IPMI:
    _CONCURRENCY = 4
    _pool = None

    def __init__(self, hostname, username, password):
        self._hostname = hostname
        self._username = username
        self._password = password
        if IPMI._pool is None:
            IPMI._pool = multiprocessing.pool.ThreadPool(self._CONCURRENCY)

    def off(self):
        IPMI._pool.apply_async(self._powerCommand, args=("off",))

    def powerCycle(self):
        IPMI._pool.apply_async(self._powerCycle)

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

    def forceBootFrom(self, boot, persistent=False):
        ALLOWED_BOOT_OPTIONS = ['disk', 'pxe', 'bios']
        if boot not in ALLOWED_BOOT_OPTIONS:
            raise Exception("Boot option %s is not allowed" % boot)

        bootenvCommand = ['chassis', 'bootdev', boot]
        if persistent:
            bootenvCommand = bootenvCommand + ['options=persistent']

        self._excuteIPMITool(bootenvCommand, retryCount=1)

    def _powerCommand(self, command):
        self._excuteIPMITool(['power', command], retryCount=10)
