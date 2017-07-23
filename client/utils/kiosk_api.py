import logging

log = logging.getLogger(__name__)


def kiosk_cmd_test(params):
    log.info("kiosk_cmd_test: %s" % params)
    return True
