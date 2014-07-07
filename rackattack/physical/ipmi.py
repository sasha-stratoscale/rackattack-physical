import subprocess
import time
import logging


class IPMI:
    def __init__(self, hostname, username, password):
        self._hostname = hostname
        self._username = username
        self._password = password

    def off(self):
        self._powerCommand("off")

    def on(self):
        self._powerCommand("on")

    def status(self):
        output = self._powerCommand("status")
        status = output.split()[-1]
        if status not in ["off", "on"]:
            raise Exception("Unknown status", dict(output = output, status = status))
        return status.split()[-1]

    def _powerCommand(self, command):
        NUMBER_OF_RETRIES = 10
        cmdLine = [
            "ipmitool", "power", command,
            "-H", str(self._hostname), "-U", self._username, "-P", self._password]
        for i in xrange(NUMBER_OF_RETRIES - 1):
            try:
                return subprocess.check_output(cmdLine, stderr=subprocess.STDOUT, close_fds=True)
            except:
                time.sleep(0.1)
        try:
            return subprocess.check_output(cmdLine, stderr=subprocess.STDOUT, close_fds=True)
        except subprocess.CalledProcessError as e:
            logging.error("Output: %(output)s", dict(output=e.output))
            raise
