from rackattack.common import globallock
from rackattack.common import timer
import time
import logging


class Allocation:
    _HEARTBEAT_TIMEOUT = 15
    _LIMBO_AFTER_DEATH_DURATION = 60

    def __init__(self, index, requirements, allocationInfo, allocated, broadcaster):
        self._index = index
        self._requirements = requirements
        self._allocationInfo = allocationInfo
        self._waiting = allocated
        for name, stateMachine in self._waiting.iteritems():
            stateMachine.setDestroyCallback(self._stateMachineSelfDestructed)
            stateMachine.assign(
                stateChangeCallback=lambda x: self._stateMachineChangedState(name, stateMachine),
                imageLabel=requirements[name]['imageLabel'],
                imageHint=requirements[name]['imageHint'])
        self._inaugurated = dict()
        self._broadcaster = broadcaster
        self._death = None
        self.heartbeat()

    def index(self):
        return self._index

    def inaugurated(self):
        assert not self.done()
        return self._inaugurated

    def allocated(self):
        result = dict(self._waiting)
        result.update(self._inaugurated)
        return result

    def done(self):
        done = len(self._inaugurated) == len(self._requirements)
        assert not done or len(self._waiting) == 0
        return done

    def free(self):
        self._die("freed")

    def withdraw(self):
        self._die("withdrawn")

    def heartbeat(self):
        if self.dead():
            return
        timer.cancelAllByTag(tag=self)
        timer.scheduleIn(timeout=self._HEARTBEAT_TIMEOUT, callback=self._heartbeatTimeout, tag=self)

    def dead(self):
        assert self._death is None or self._inaugurated is None
        if self._death is None:
            return None
        return self._death['reason']

    def deadForAWhile(self):
        if not self.dead():
            return False
        return self._death['when'] < time.time() - self._LIMBO_AFTER_DEATH_DURATION

    def _heartbeatTimeout(self):
        self._die("heartbeat timeout")

    def _die(self, reason):
        assert not self.dead()
        logging.info("Allocation dies of '%(reason)s'", dict(reason=reason))
        for stateMachine in list(self._waiting.values()) + list(self._inaugurated.values()):
            stateMachine.unassign()
            stateMachine.setDestroyCallback(None)
            self._freePool.put(stateMachine)
        self._inaugurated = None
        self._death = dict(when=time.time(), reason=reason)
        timer.cancelAllByTag(tag=self)
        self._broadcaster.allocationChangedState(self._index)

    def _stateMachineChangedState(self, name, stateMachine):
        if stateMachine.state() == hoststatemachine.STATE_INAUGURATION_DONE:
            assert name in self._waiting
            del self._waiting[name]
            self._inaugurated[name] = stateMachine
            self._broadcaster.allocationProviderMessage(
                allocationID=self._index,
                message="host %s inaugurated successfully" % stateMachine.hostImplementation().ipAddress())
            if self.done():
                self._broadcaster.allocationChangedState(self._index)

    def _stateMachineSelfDestructed(self, stateMachine):
        self._hosts.destroy(stateMachine)
        for k, v in self._waiting.iteritems():
            if v is stateMachine:
                del self._waiting[k]
                break
        for k, v in self._inaugurated.iteritems():
            if v is stateMachine:
                del self._inaugurated[k]
                break
        self._die("Host %s unable to be inaugurated" % stateMachine.hostImplementation().index())
