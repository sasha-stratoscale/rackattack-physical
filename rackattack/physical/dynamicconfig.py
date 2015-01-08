import signal
from rackattack.common import globallock
from rackattack.physical import config
from rackattack.physical import host
from rackattack.common import hoststatemachine
import yaml
import logging


class DynamicConfig:
    def __init__(self, hosts, dnsmasq, inaugurate, tftpboot, freePool, allocations):
        self._hosts = hosts
        self._dnsmasq = dnsmasq
        self._inaugurate = inaugurate
        self._tftpboot = tftpboot
        self._freePool = freePool
        self._allocations = allocations
        self._rack = []
        self._offlineHosts = dict()
        self._onlineHosts = dict()
        signal.signal(signal.SIGHUP, lambda *args: self._reload())
        self._reload()

    def _loadRackYAML(self):
        logging.info("Reading %(file)s", dict(file=config.RACK_YAML))
        with open(config.RACK_YAML) as f:
            return yaml.load(f.read())

    def _reload(self):
        logging.info("Reloading configuration")
        rack = self._loadRackYAML()
        with globallock.lock():
            for hostData in rack['HOSTS']:
                if hostData['id'] in self._offlineHosts or hostData['id'] in self._onlineHosts:
                    if hostData['id'] in self._onlineHosts and hostData.get('offline', False):
                        logging.info("Host %(host)s has been taken offline", dict(host=hostData['id']))
                        hostInstance = self._onlineHosts[hostData['id']]
                        assert hostInstance.id() == hostData['id']
                        del self._onlineHosts[hostInstance.id()]
                        self._offlineHosts[hostInstance.id()] = hostInstance
                        hostInstance.turnOff()
                        stateMachine = self._findStateMachine(hostInstance)
                        if stateMachine is not None:
                            for allocation in self._allocations.all():
                                if stateMachine in allocation.allocated().values():
                                    allocation.withdraw("node taken offline")
                            assert stateMachine in self._freePool.all()
                            self._freePool.takeOut(stateMachine)
                            self._hosts.destroy(stateMachine)
                    elif hostData['id'] in self._offlineHosts and not hostData.get('offline', False):
                        logging.info("Host %(host)s has been taken back online", dict(host=hostData['id']))
                        hostInstance = self._offlineHosts[hostData['id']]
                        assert hostInstance.id() == hostData['id']
                        del self._offlineHosts[hostInstance.id()]
                        self._onlineHosts[hostInstance.id()] = hostInstance
                        self._startUsingHost(hostInstance)
                else:
                    self._newHostInConfiguration(hostData)

    def _newHostInConfiguration(self, hostData):
        chewed = dict(hostData)
        if 'offline' in chewed:
            del chewed['offline']
        hostInstance = host.Host(index=self._availableIndex(), **chewed)
        logging.info("Adding host %(id)s - %(ip)s", dict(
            id=hostInstance.id(), ip=hostInstance.ipAddress()))
        self._dnsmasq.add(hostData['primaryMAC'], hostInstance.ipAddress())
        if hostData.get('offline', False):
            self._offlineHosts[hostData['id']] = hostInstance
            hostInstance.turnOff()
            logging.info('Host %(host)s added in offline state', dict(host=hostInstance.id()))
        else:
            self._onlineHosts[hostData['id']] = hostInstance
            self._startUsingHost(hostInstance, True)
            logging.info('Host %(host)s added in online state', dict(host=hostInstance.id()))

    def _startUsingHost(self, hostInstance, clearDisk=False):
        stateMachine = hoststatemachine.HostStateMachine(
            hostImplementation=hostInstance,
            inaugurate=self._inaugurate,
            tftpboot=self._tftpboot,
            freshVMJustStarted=False,
            clearDisk=clearDisk)
        self._hosts.add(stateMachine)
        self._freePool.put(stateMachine)

    def _findStateMachine(self, hostInstance):
        for stateMachine in self._hosts.all():
            if stateMachine.hostImplementation() is hostInstance:
                return stateMachine
        return None

    def _availableIndex(self):
        return 1 + len(self._onlineHosts) + len(self._offlineHosts)
