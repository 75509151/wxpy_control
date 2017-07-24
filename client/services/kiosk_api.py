import logging

# init log
log = logging.getLogger(__name__)


ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)
log.setLevel(logging.DEBUG)


def kiosk_cmd_test(params):
    log.info("kiosk_cmd_test in another dir: %s" % params)
    return True
