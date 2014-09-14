import logging
import pty
import os
import time
import subprocess
import threading
from rackattack.physical import config
from rackattack.tcp import suicide


class SerialOverLan(threading.Thread):
    def __init__(self, hostname, username, password):
        self._hostname = hostname
        self._username = username
        self._password = password
        self._serialFile = self._getSerialFilePath()
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        RETRIES = 5
        for i in xrange(RETRIES):
            logging.info("trying to establish SOL connection to %(hostname)s", dict(
                hostname=self._hostname))
            stdin, popen = self._popenSOL()
            try:
                popen.wait()
            finally:
                os.close(stdin)
            logging.error("SOL connection to %(hostname)s is broken", dict(hostname=self._hostname))
        logging.error(
            "All retries to establish SOL connection to %(hostname)s failed, comitting suicide", dict(
                hostname=self._hostname))
        suicide.killSelf()

    def fetchSerialLog(self):
        with open(self._serialFile) as f:
            return f.read()

    def truncateSerialLog(self):
        open(self._serialFile, 'w').close()

    def _popenSOL(self):
        self.truncateSerialLog()
        subprocess.call(self._getSolCommand("deactivate"))
        master, slave = pty.openpty()
        try:
            with open(self._serialFile, "w") as outputFile:
                return master, subprocess.Popen(
                    self._getSolCommand("activate"), stdin=slave,
                    stderr=subprocess.STDOUT, stdout=outputFile, close_fds=True)
        finally:
            os.close(slave)

    def _getSolCommand(self, action):
        NUMBER_OF_RETRIES = "10"
        return ("ipmitool", "-I", "lanplus", "-H", self._hostname,
                "-U", self._username, "-P", self._password, "sol", action, "-R", NUMBER_OF_RETRIES)

    def _getSerialFilePath(self):
        if not os.path.isdir(config.SERIAL_LOGS_DIRECTORY):
            os.makedirs(config.SERIAL_LOGS_DIRECTORY)
        return os.path.join(config.SERIAL_LOGS_DIRECTORY, self._hostname + "-serial.txt")
