from rackattack.virtual import sh
import subprocess
import os

_IP_ADDRESS_FORMAT = "192.168.1.%d"
GATEWAY_IP_ADDRESS = _IP_ADDRESS_FORMAT % 1
BOOTSERVER_IP_ADDRESS = _IP_ADDRESS_FORMAT % 1
NETMASK = '255.255.255.0'
_NETWORK_PREFIX = "192.168.1."
LAST_INDEX = 200


def setGatewayIP(ip):
    global GATEWAY_IP_ADDRESS
    GATEWAY_IP_ADDRESS = ip


def ipAddressFromHostIndex(index):
    return _IP_ADDRESS_FORMAT % (10 + index)


FIRST_IP = ipAddressFromHostIndex(0)
LAST_IP = ipAddressFromHostIndex(LAST_INDEX)


def sshPortFromHostIndex(index):
    return 2010 + index


def setUpStaticPortForwardingForSSH(publicInterface):
    deviceName = _findPublicInterface(publicInterface)
    for index in xrange(LAST_INDEX + 1):
        subprocess.call([
            "iptables", '-D', 'PREROUTING', '-t', 'nat', '-i', deviceName,
            '-p', 'tcp', '--dport', str(sshPortFromHostIndex(index)), '-j', 'DNAT'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    for index in xrange(LAST_INDEX + 1):
        sh.run([
            "iptables", "-A", "PREROUTING", "-t", "nat", "-i", deviceName,
            "-p", "tcp", "--dport",  str(sshPortFromHostIndex(index)), "-j", "DNAT",
            "--to", "%s:22" % ipAddressFromHostIndex(index)])
    subprocess.call([
        "iptables", "-t", "nat", "-D", "POSTROUTING", "-o", deviceName, "-j", 'MASQUERADE'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    sh.run([
        "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", deviceName, "-j", 'MASQUERADE'])


def translateSSHCredentials(index, credentials, publicNATIP, peer):
    if peer[0].startswith(_NETWORK_PREFIX):
        return credentials
    assert ipAddressFromHostIndex(index) == credentials['hostname']
    return dict(credentials, hostname=publicNATIP, port=sshPortFromHostIndex(index))


def _findPublicInterface(publicInterface):
    for deviceName in os.listdir("/sys/class/net"):
        if publicInterface == deviceName:
            return publicInterface
        with open("/sys/class/net/%s/address" % deviceName) as f:
            address = f.read().strip()
        if address == publicInterface:
            return deviceName
    raise Exception("public interface '%s' not found" % publicInterface)
