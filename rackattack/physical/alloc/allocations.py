from rackattack.physical.alloc import allocation
from rackattack.physical.alloc import priority
from rackattack.common import globallock


class Allocations:
    def __init__(self, broadcaster, hosts, freePool):
        self._broadcaster = broadcaster
        self._hosts = hosts
        self._freePool = freePool
        self._allocations = []
        self._index = 1

    def create(self, requirements, allocationInfo):
        assert globallock.assertLocked()
        self._cleanup()
        priorityInstance = priority.Priority(
            requirements=requirements, allocationInfo=allocationInfo,
            freePool=self._freePool, allocations=self._allocations)
        allocated = priorityInstance.allocated()
        alloc = allocation.Allocation(
            index=self._index, requirements=requirements, allocationInfo=allocationInfo,
            allocated=allocated, broadcaster=self._broadcaster)
        self._allocations.append(alloc)
        self._index += 1
        return alloc

    def byIndex(self, index):
        assert globallock.assertLocked()
        self._cleanup()
        for alloc in self._allocations:
            if alloc.index() == index:
                return alloc
        raise IndexError("No such allocation")

    def all(self):
        assert globallock.assertLocked()
        self._cleanup()
        return self._allocations

    def _cleanup(self):
        self._allocations = [a for a in self._allocations if not a.deadForAWhile()]
