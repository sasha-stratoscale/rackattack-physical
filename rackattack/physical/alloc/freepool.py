from rackattack.common import globallock


class FreePool:
    def __init__(self, hosts):
        self._hosts = hosts
        self._pool = []
        self._putListeners = []

    def put(self, hostStateMachine):
        assert globallock.assertLocked()
        self._pool.append(hostStateMachine)
        hostStateMachine.setDestroyCallback(self._hostSelfDestructed)
        for listener in self._putListeners:
            listener()

    def all(self):
        assert globallock.assertLocked()
        for hostStateMachine in self._pool:
            yield hostStateMachine

    def takeOut(self, hostStateMachine):
        assert globallock.assertLocked()
        self._pool.remove(hostStateMachine)

    def registerPutListener(self, callback):
        assert callback not in self._putListeners
        self._putListeners.append(callback)

    def unregisterPutListener(self, callback):
        assert callback in self._putListeners
        self._putListeners.remove(callback)

    def _hostSelfDestructed(self, hostStateMachine):
        assert globallock.assertLocked()
        self._hosts.destroy(hostStateMachine)
        self._pool.remove(hostStateMachine)
