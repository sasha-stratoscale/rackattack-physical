import unittest
import mock
from mock import patch
from rackattack.physical import ipmi
import subprocess


def fake_apply_async(func, args=(), kwds={}, callback=None):
    func(*args, **kwds)
    if callback is not None:
        callback()


class Test(unittest.TestCase):

    def setUp(self):
        self.tested = ipmi.IPMI('hostname', 'username', 'password')
        self.tested._worker.apply_async = fake_apply_async

    @patch('subprocess.check_output', return_value='')
    def test_IPMI_set_pxe_configuration(self, *_args):
        self.tested.forceBootFrom('pxe')
        self.assertEquals(subprocess.check_output.call_count, 1)
        args, _unused = subprocess.check_output.call_args
        self.assertEqual(['ipmitool', '-H', 'hostname', "-U", "username",
                          "-P", "password", "chassis", "bootdev", "pxe", "options=persistent"], args[0])

    def test_IPMI_set_pxe_configurationFailCallTwice(self, *_args):
        subprocess.check_output = mock.Mock()
        subprocess.check_output.side_effect = subprocess.CalledProcessError(1, "Bad command")
        self.assertRaises(subprocess.CalledProcessError, self.tested.forceBootFrom, 'pxe')
        self.assertEquals(subprocess.check_output.call_count, 2)

    def test_IPMI_reset_without_boot_params(self, *_args):
        subprocess.check_output = mock.Mock()
        self.tested.powerCycle()
        self.assertEquals(subprocess.check_output.call_count, 2)

        firstCallArgs = subprocess.check_output.call_args_list[0][0][0]
        secondCallArgs = subprocess.check_output.call_args_list[1][0][0]
        self.assertEquals(firstCallArgs, ['ipmitool', '-H', 'hostname',
                                          '-U', 'username', '-P', 'password', 'power', 'off'])
        self.assertEquals(secondCallArgs, ['ipmitool', '-H', 'hostname',
                                           '-U', 'username', '-P', 'password', 'power', 'on'])

if __name__ == '__main__':
    unittest.main()
