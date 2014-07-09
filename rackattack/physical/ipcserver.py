import threading
import zmq
import logging
import simplejson
from rackattack.tcp import heartbeat
from rackattack.tcp import suicide
from rackattack import api
from rackattack.common import globallock


class IPCServer(threading.Thread):
    def __init__(self, tcpPort, allocations):
        self._allocations = allocations
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind("tcp://*:%d" % tcpPort)
        threading.Thread.__init__(self)
        self.daemon = True
        threading.Thread.start(self)

    def _cmd_handshake(self, version):
        if version != api.VERSION:
            raise Exception(
                "Rackattack API version on the client side is '%s', and '%s' on the provider" % (
                    version, api.VERSION))

    def _cmd_allocate(self, requirements, allocationInfo):
        allocation = self._allocations.create(requirements, allocationInfo)
        return allocation.index()

    def _cmd_allocation__nodes(self, id):
        allocation = self._allocations.byIndex(id)
        if allocation.dead():
            raise Exception("Must not fetch nodes from a dead allocation")
        if not allocation.done():
            raise Exception("Must not fetch nodes from a not done allocation")
        result = {}
        for name, stateMachine in allocation.allocated().iteritems():
            host = stateMachine.hostImplementation()
            result[name] = dict(
                id=host.id(), primaryMACAddress=host.primaryMACAddress(),
                secondaryMACAddress=host.secondaryMACAddress(), ipAddress=host.ipAddress())
        return result

    def _cmd_allocation__free(self, id):
        allocation = self._allocations.byIndex(id)
        allocation.free()

    def _cmd_allocation__done(self, id):
        allocation = self._allocations.byIndex(id)
        return allocation.done()

    def _cmd_allocation__dead(self, id):
        allocation = self._allocations.byIndex(id)
        return allocation.dead()

    def _cmd_heartbeat(self, ids):
        for id in ids:
            allocation = self._allocations.byIndex(id)
            allocation.heartbeat()
        return heartbeat.HEARTBEAT_OK

    def _cmd_node__rootSSHCredentials(self, allocationID, nodeID):
        allocation = self._allocations.byIndex(allocationID)
        for stateMachine in allocation.inaugurated().values():
            if stateMachine.hostImplementation().id() == nodeID:
                return stateMachine.hostImplementation().rootSSHCredentials()
        raise Exception("Node with id '%s' was not found in this allocation" % nodeID)

    def run(self):
        try:
            while True:
                try:
                    self._work()
                except:
                    logging.exception("Handling")
        except:
            logging.exception("Virtual IPC server aborts")
            suicide.killSelf()
            raise

    def _work(self):
        message = self._socket.recv(0)
        try:
            incoming = simplejson.loads(message)
            handler = getattr(self, "_cmd_" + incoming['cmd'])
            with globallock.lock:
                response = handler(** incoming['arguments'])
        except Exception, e:
            logging.exception('Handling')
            response = dict(exceptionString=str(e), exceptionType=e.__class__.__name__)
        self._socket.send_json(response)
