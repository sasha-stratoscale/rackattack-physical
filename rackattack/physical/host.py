from rackattack.physical import ipmi
from rackattack.physical import network
from rackattack.physical import config
from rackattack.physical import serialoverlan
import logging
import os


class Host:
    def __init__(self, index, bootMAC, ipmiLogin, primaryMAC, secondaryMAC):
        self._index = index
        self._bootMAC = bootMAC
        self._ipmiLogin = ipmiLogin
        self._primaryMAC = primaryMAC
        self._secondaryMAC = secondaryMAC
        self._ipmi = ipmi.IPMI(**ipmiLogin)
        self._sol = serialoverlan.SerialOverLan(**ipmiLogin)

    def index(self):
        return self._index

    def id(self):
        return self._index

    def primaryMACAddress(self):
        return self._primaryMAC

    def secondaryMACAddress(self):
        return self._secondaryMAC

    def ipAddress(self):
        return network.ipAddressFromHostIndex(self._index)

    def rootSSHCredentials(self):
        return dict(hostname=self.ipAddress(), username="root", password=config.ROOT_PASSWORD)

    def coldRestart(self):
        logging.info("Cold booting host %(index)d", dict(index=self._index))
        self._ipmi.off()
        self._ipmi.on()

    def destroy(self):
        logging.info("Host %(index)d destroyed", dict(index=self._index))

    def fulfillsRequirement(self, requirement):
        return True

    def fetchSerialLog(self):
        return self._sol.fetchSerialLog()

    def truncateSerialLog(self):
        self._sol.truncateSerialLog()
