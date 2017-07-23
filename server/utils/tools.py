from .access_agent import Server as AgentServer
import logging

log = logging.getLogger(__name__)


def _kioskid2port(kiosk_id, prefix=1):
    """ Get the port according to hostname, the kiosk is allowed from A000
    to J999.
    e.g. A000 ==> 21000
    @param prefix(int): the prefix digit for the
    @return: the port converted from the hostname
    @rtype: string
    """
    port_info = kiosk_id.split("-")[-1]
    port = chr(ord(port_info[0]) - 0x10)  # cover A to 1, B to 2, etc
    # check if the port is valid, 0 is as default
    if not port.isdigit():
        port = "0"
    port += port_info[1:]

    return str(prefix) + port


def call_kiosk(device_id, call_method, params, access_agent_host, timeout=30):
    """call kiosk's service
    @param device_id(str):call device's id
    @param call_method(str):
    @param params(dict):
    @return: {"state": "", "data":""}
              state: "success" or "error" or "offline" or upgrade
              data: success: result
                    error: exception msg
                    offline: None
                    upgrade: error msg
    """
    result = {"state": "offline", "data": None}
    agent_service = None
    if not device_id:
        return {"state": "error", "data": "Required Kiosk ID."}
    try:
        agent_service = AgentServer(device_id,
                                    log,
                                    access_agent_host,
                                    _kioskid2port(device_id),
                                    timeout)
        try:
            call_result = agent_service.do_command(call_method, (params, ))
            result = {"state": "success", "data": call_result}
        except Exception, ex:
            if "[Errno 10061]" not in str(ex):
                raise
            log.warning("Error: %s is offline or rejects connection." % device_id)
    except Exception, ex:
        log.error("fatal error: %s" % ex)
        if "No function or attr" in str(ex):
            result = {"state": "upgrade", "data": str(ex)}
        else:
            result = {"state": "error", "data": str(ex)}
    del agent_service
    return result
