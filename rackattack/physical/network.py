_IP_ADDRESS_FORMAT = "192.168.1.%d"
GATEWAY_IP_ADDRESS = _IP_ADDRESS_FORMAT % 1
NETMASK = '255.255.255.0'


def ipAddressFromVMIndex(index):
    return _IP_ADDRESS_FORMAT % (10 + index)



FIRST_IP = ipAddressFromVMIndex(0)
LAST_IP = ipAddressFromVMIndex(200)
