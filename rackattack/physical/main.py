import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from rackattack.ssh import connection
connection.discardParamikoLogs()
connection.discardSSHDebugMessages()
import time
import argparse
from rackattack.physical import config
from rackattack.physical import network
from rackattack.physical import host
import rackattack.virtual.handlekill
from rackattack.common import dnsmasq
from rackattack.common import tftpboot
from rackattack.common import inaugurate
from rackattack.common import timer
from rackattack.common import hosts
from rackattack.common import hoststatemachine
from rackattack.common import globallock
from rackattack.physical.alloc import freepool
from rackattack.physical.alloc import allocations
from rackattack.physical import ipcserver
from rackattack.tcp import publish
import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--requestPort", default=1014, type=int)
parser.add_argument("--subscribePort", default=1015, type=int)
parser.add_argument("--rackYAML")
parser.add_argument("--serialLogsDirectory")
parser.add_argument("--configurationFile")
args = parser.parse_args()

if args.rackYAML:
    config.RACK_YAML = args.rackYAML
if args.serialLogsDirectory:
    config.SERIAL_LOGS_DIRECTORY = args.serialLogsDirectory
if args.configurationFile:
    config.CONFIGURATION_FILE = args.configurationFile

with open(config.RACK_YAML) as f:
    rack = yaml.load(f.read())
with open(config.CONFIGURATION_FILE) as f:
    conf = yaml.load(f.read())

network.setUpStaticPortForwardingForSSH(conf['PUBLIC_INTERFACE'])
timer.TimersThread()
tftpbootInstance = tftpboot.TFTPBoot(
    netmask=network.NETMASK,
    inauguratorServerIP=network.GATEWAY_IP_ADDRESS,
    osmosisServerIP=conf['OSMOSIS_SERVER_IP'],
    rootPassword=config.ROOT_PASSWORD,
    withLocalObjectStore=True)
dnsmasq.DNSMasq.killAllPrevious()
dnsmasqInstance = dnsmasq.DNSMasq(
    tftpboot=tftpbootInstance,
    serverIP=network.GATEWAY_IP_ADDRESS,
    netmask=network.NETMASK,
    firstIP=network.FIRST_IP,
    lastIP=network.LAST_IP,
    gateway=network.GATEWAY_IP_ADDRESS,
    nameserver=network.GATEWAY_IP_ADDRESS)
inaugurateInstance = inaugurate.Inaugurate(bindHostname=network.GATEWAY_IP_ADDRESS)
publishInstance = publish.Publish(tcpPort=args.subscribePort, localhostOnly=False)
hostsInstance = hosts.Hosts()
freePool = freepool.FreePool(hostsInstance)
with globallock.lock:
    for hostData in rack['HOSTS']:
        hostInstance = host.Host(index=hostsInstance.availableIndex(), **hostData)
        dnsmasqInstance.add(hostData['primaryMAC'], hostInstance.ipAddress())
        stateMachine = hoststatemachine.HostStateMachine(
            hostImplementation=hostInstance, inaugurate=inaugurateInstance, tftpboot=tftpbootInstance,
            freshVMJustStarted=False)
        hostsInstance.add(stateMachine)
        freePool.put(stateMachine)
        logging.info("Added host %(id)s - %(ip)s", dict(id=hostInstance.id(), ip=hostInstance.ipAddress()))
allocationsInstance = allocations.Allocations(
    broadcaster=publishInstance, hosts=hostsInstance, freePool=freePool,
    osmosisServer=conf['OSMOSIS_SERVER_IP'])
server = ipcserver.IPCServer(
    tcpPort=args.requestPort,
    publicIP=conf['PUBLIC_IP'],
    osmosisServerIP=conf['OSMOSIS_SERVER_IP'],
    allocations=allocationsInstance,
    hosts=hostsInstance)
logging.info("Physical RackAttack up and running")
while True:
    time.sleep(1000 * 1000)
