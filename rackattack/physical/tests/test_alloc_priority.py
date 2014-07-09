import unittest
from rackattack.common import globallock
from rackattack.physical.alloc import priority
from rackattack import api


class Empty:
    pass


class HostStateMachine:
    def __init__(self, name):
        self.name = name

    def hostImplementation(self):
        return Host(self.name)


class Host:
    def __init__(self, name):
        self.name = name

    def fulfillsRequirement(self, requirement):
        return True


class FreePool:
    def __init__(self):
        self.pool = []

    def all(self):
        return self.pool

    def takeOut(self, stateMachine):
        self.pool.remove(stateMachine)


class Allocation:
    def __init__(self, freePool, nice):
        self._allocationInfo = api.AllocationInfo(user='test', purpose='user', nice=nice).__dict__
        self.freePool = freePool
        self.allocatedHosts = []

    def withdraw(self):
        self.freePool.pool += self.allocatedHosts
        self.allocatedHosts = None

    def allocated(self):
        return self.allocatedHosts

    def allocationInfo(self):
        return self._allocationInfo


class Test(unittest.TestCase):
    def setUp(self):
        globallock.lock.acquire()
        self.freePool = FreePool()
        self.allocationInfo = api.AllocationInfo(user='test', purpose='user', nice=0.5).__dict__
        self.allocations = []
        self.requirements = {}

    def tearDown(self):
        globallock.lock.release()

    def construct(self):
        self.tested = priority.Priority(
            self.requirements, self.allocationInfo, self.freePool, self.allocations)

    def test_NoHostsAllocationFailes(self):
        self.requirements['yuvu'] = 'spec'
        with self.assertRaises(priority.OutOfResourcesError):
            self.construct()

    def test_AllocateOneFromFreePool(self):
        self.freePool.pool.append(HostStateMachine('host1'))
        self.requirements['yuvu'] = 'spec'
        self.construct()
        self.assertEquals(len(self.tested.allocated()), 1)
        self.assertEquals(self.tested.allocated()['yuvu'].name, 'host1')
        self.assertEquals(len(self.freePool.pool), 0)

    def test_AllocateOneByWithdrawingAnAllocation(self):
        self.allocations.append(Allocation(self.freePool, 0.9))
        self.allocations[0].allocatedHosts.append(HostStateMachine('host1'))
        self.requirements['yuvu'] = 'spec'
        self.construct()
        self.assertEquals(len(self.tested.allocated()), 1)
        self.assertEquals(self.tested.allocated()['yuvu'].name, 'host1')
        self.assertEquals(len(self.freePool.pool), 0)
        self.assertIs(self.allocations[0].allocatedHosts, None)

    def test_DoesNotTakeMachinesFromHigherPriority(self):
        self.allocations.append(Allocation(self.freePool, 0.1))
        self.allocations[0].allocatedHosts.append(HostStateMachine('host1'))
        self.requirements['yuvu'] = 'spec'
        with self.assertRaises(priority.OutOfResourcesError):
            self.construct()
        self.assertEquals(len(self.allocations[0].allocatedHosts), 1)

    def test_AllocateOneFromFreePool_DontTouchExisting(self):
        self.allocations.append(Allocation(self.freePool, 0.9))
        self.allocations[0].allocatedHosts.append(HostStateMachine('host2'))
        self.freePool.pool.append(HostStateMachine('host1'))
        self.requirements['yuvu'] = 'spec'
        self.construct()
        self.assertEquals(len(self.tested.allocated()), 1)
        self.assertEquals(self.tested.allocated()['yuvu'].name, 'host1')
        self.assertEquals(len(self.freePool.pool), 0)
        self.assertEquals(len(self.allocations[0].allocatedHosts), 1)


if __name__ == '__main__':
    unittest.main()
