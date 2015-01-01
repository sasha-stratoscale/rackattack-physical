import logging

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('network').setLevel(logging.DEBUG)
logging.getLogger('network').propagate = False
logging.getLogger().setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("/var/log/rackattack.physical.network.log")
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logging.getLogger('network').addHandler(handler)
