#
""" Access agent.
##
##
"""
# Import from standard library.
import uuid
import cPickle
import socket
import struct
import time
import logging
from kiosk_info import get_kiosk_id

#                    Configuration.
#======================================================
# dCeP
MAGIC = 0x64436550

MSG_TYPE_REQUEST = 0x01
MSG_TYPE_REPLY = 0x02
MSG_TYPE_BATCH_REQUEST = 0x03
MSG_TYPE_VALIDATE_CHALLENGE = 0x04
MSG_TYPE_VALIDATE_CONNECTION = 0x05
MSG_TYPE_CLOSE = 0x06
MSG_TYPE_UNKNOWN = 0xff

SUCCESS = 0
AGENT_EXCEPTION = 1
UNKNOWN_EXCEPTION = 2

TRANSPORT_CLOSED = 0
TRANSPORT_CONNECTED = 1
TRANSPORT_CLOSING = 2

DEFAULT_TIMEOUT = 15  # second

MAX_MESSAGE_LENGTH = 10485760  # 10M

#======================================================
#                    Exception
#======================================================


class BaseException(Exception):
    def __init__(self, msg=""):
        Exception.__init__(self, msg)


class ProtocolException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)


class CodecException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)


class CommunicateException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)


class UnkownException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)


class NoMethodException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)


class UserException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)

#======================================================
#                    BaseObj
#======================================================


class AgentBase(object):
    """ Base object.
    """

    def __init__(self, log=None, _uuid=None):
        if _uuid:
            self._id = _uuid
        else:
            self._id = str(uuid.uuid4())
        self.log = None
        if log:
            self.log = log

    def __del__(self):
        del self.log

    def _get_id(self):
        return self._id

#======================================================
#      Protocol, DCECodec, Request, Reply
#======================================================


class AgentCodec(AgentBase):
    """ Codec """

    def __init__(self):
        AgentBase.__init__(self)

    def __del__(self):
        AgentBase.__del__(self)

    def encode(self, body):
        try:
            return cPickle.dumps(body)
        except Exception, ex:
            raise CodecException(str(ex))

    def decode(self, msg):
        try:
            return cPickle.loads(msg)
        except Exception, ex:
            raise CodecException(str(ex))


class Request(AgentBase):
    """ Request """

    def __init__(self, method_name, params, one_way=0, _type=MSG_TYPE_REQUEST):
        AgentBase.__init__(self)
        self._method_name = method_name
        self._params = params
        self._one_way = one_way
        self._type = _type

    def __del__(self):
        AgentBase.__del__(self)


class Reply(AgentBase):
    """ Reply """

    def __init__(self, reqId, status, body, _type=MSG_TYPE_REPLY):
        AgentBase.__init__(self)
        self._rid = reqId
        self._status = status
        self._body = body
        self._type = _type

    def __del__(self):
        AgentBase.__del__(self)


class Protocol(object):
    """ Protocol of Agent. """
    head_fmt = "!iBQ"
    head_size = struct.calcsize(head_fmt)

    def __init__(self):
        pass

    def request_to_raw(self, req):
        if req._one_way:
            _id = "00000000-0000-0000-0000-000000000000"
        else:
            _id = str(req._id)
        codec = AgentCodec()
        body = codec.encode((_id, req._method_name, req._params))
        length = len(body)
        # print "body in request_to_raw: %s %s" % (l, body)
        head = struct.pack(self.head_fmt, MAGIC, req._type, length)
        # print "head in request_to_raw:", head
        return (_id, head + body)

    def reply_to_raw(self, reply):
        codec = AgentCodec()
        body = codec.encode((reply._rid, reply._status, reply._body))
        length = len(body)
        # print "body in reply_to_raw: %s %s" % (l, body)
        head = struct.pack(self.head_fmt, MAGIC, reply._type, length)
        # print "head in reply_to_raw:", head
        return head + body

    def parse_head(self, head):
        try:
            head_info = struct.unpack(self.head_fmt, head)

            if head_info[0] != MAGIC:
                raise ProtocolException("Magic number error")

            codec = AgentCodec()
            #(type,bodysize,codec)
            return (head_info[1], head_info[2], codec)
        except Exception, ex:
            raise ProtocolException(str(ex))

    def get_head_size(self):
        return self.head_size

#======================================================
#                  Endpoint
#======================================================


class Endpoint(AgentBase):
    """ Endpoint server side or kiosk side. """

    def __init__(self, kiosk_id, log, default_host, default_port, timeout, side="server"):
        AgentBase.__init__(self, log)
        self.kiosk_id = kiosk_id
        self.timeout = timeout
        self.default_host = default_host
        self.default_port = default_port
        self._sock = None
        if side.lower() not in ("server", "kiosk"):
            raise UnkownException("Invalid Endpoint side %s" % side)
        self.side = side

    def __del__(self):
        AgentBase.__del__(self)

    def get_host_port(self):
        """ Get port. side is server/kiosk """
        port = ""
        if self.side.lower() == "server":
            prefix = 1
            tmp = chr(ord(self.kiosk_id[3]) - 0x10)  # cover A to 1, B to 2, etc
            tmp += self.kiosk_id[4:]
            port = str(prefix) + tmp
        elif self.side.lower() == "kiosk":
            port = str(self.default_port)
        else:
            raise CommunicateException("Cannot get the port for %s" % self.side)

        if port and port.isdigit():
            return (self.default_host, int(port))
        else:
            raise CommunicateException("Invalid port %s" % port)

    def parse_requst(self, request):
        """ Parse request. """
        pass

    def parse_reply(self, reply):
        """ Parse reply. """
        pass

    def on_recv(self, timeout=0):
        pass

    def recvall(self, size):
        pass

#======================================================
#                  Server side
#======================================================


class Server(Endpoint):
    """ Server side. """

    def __init__(self, kiosk_id, log, default_host, default_port="", timeout=DEFAULT_TIMEOUT):
        Endpoint.__init__(self, kiosk_id, log, default_host, default_port, timeout)

    def __del__(self):
        try:
            Endpoint.__del__(self)
            if hasattr(self.sock, "close"):
                self.sock.close()
            del self.sock
        except:
            pass

    def do_command(self, func_name, params=()):
        """ Do command for kiosk.
        kioskId is just compatible to the DCE access node.
        """
        return self.__call__(func_name, params)

    def is_online(self):
        """ Check if the kiosk is online """
        return self.do_command("access_agent_is_on_line")

    def __call__(self, func_name, params):
        """ """
        try:
            req = Request(func_name, params)
            protocol = Protocol()
            req_id, send_msg = protocol.request_to_raw(req)
            # print reqId, sendMsg
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host, port = self.get_host_port()
            # print host, port
            self.sock.connect((host, port))
            self.sock.settimeout(self.timeout)

            # Retry 2 times.
            for _i in range(2):
                self.sock.sendall(send_msg)
                reply_id, reply_body = self.on_recv()
                if reply_id == req_id:
                    reply_status, reply_msg = reply_body
                    if reply_status == SUCCESS:
                        return reply_msg
                    elif reply_status == AGENT_EXCEPTION:
                        raise reply_msg
            if reply_id != req_id:
                m = "Reply RID not matched, wanted:%s, got:%s" % (req_id, reply_id)
                self.log.error(m)
                raise ProtocolException(m)
        except socket.error, ex:
            self.log.error("Socket error when execute %s(%s): %s" % (func_name, params, ex))
            raise
        except Exception, ex:
            self.log.error("Error when execute %s(%s): %s" % (func_name, params, ex))
            raise

    def on_recv(self, timeout=0):
        """ recieve reply. """
        protocol = Protocol()
        head_size = protocol.get_head_size()
        head = self.recvall(head_size)
        # print "head", head
        if len(head) != head_size:
            raise CommunicateException("Connection may be closed by peer")

        _type, size, codec = protocol.parse_head(head)
        body = ""

        while size > 0:
            buf = self.recvall(size)  # raise CommunicateException
            body = body + buf
            size = size - len(buf)

        try:
            body = codec.decode(body)
        except Exception, ex:
            raise ProtocolException("Decode Message Body Error: %s" % ex)

        if _type == MSG_TYPE_REPLY:
            if len(body) < 3:
                raise ProtocolException("Message Body Content Error")
            reply_rid = body[0]
            reply_body = (body[1], body[2])
            return reply_rid, reply_body
        else:
            raise ProtocolException("Message Type Error")

    def recvall(self, size):
        """ recieve all. """
        try:
            s = size
            buf = ""
            while True:
                b = self.sock.recv(s)
                buf = buf + b
                s = s - len(b)
                if s == 0 or not b:
                    return buf
        except Exception, ex:
            raise CommunicateException("RecvALL Error:%s" % ex)

#======================================================
#                  Kiosk side
#======================================================


class Kiosk(Endpoint):
    """ Kiosk side.
    """

    def __init__(self, kiosk_id, call_module_path, log, default_host, default_port="", timeout=DEFAULT_TIMEOUT):
        Endpoint.__init__(self, kiosk_id, log, default_host, default_port, timeout, "kiosk")
        self.call_module_path = call_module_path

    def __del__(self):
        Endpoint.__del__(self)

    def run(self):
        try:
            kiosk_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            kiosk_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            host, port = self.get_host_port()
            kiosk_sock.bind((host, port))
            kiosk_sock.listen(5)
            while True:
                time.sleep(0.01)
                sock, addr = kiosk_sock.accept()
                # print sock, addr
                self.sock = sock
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    try:
                        self.on_recv()
                    finally:
                        self.sock.close()
                except Exception, ex:
                    if hasattr(self.log, "error"):
                        self.log.error("Error onRecv for %s: %s" % (addr, ex))
        except socket.error, ex:
            self.log.error("sock error,sleep 15s, err:%s" % str(ex))
            time.sleep(15)
        except Exception, ex:
            if hasattr(self.log, "error"):
                self.log.error("[Kiosk] Error in run: %s" % ex)

    def recvall(self, size):
        """ recieve all. """
        try:
            s = size
            buf = ""
            while True:
                b = self.sock.recv(s)
                buf = buf + b
                s = s - len(b)
                if s == 0 or not b:
                    return buf
        except Exception, ex:
            e = "RecvALL Error:%s" % ex
            if hasattr(self.log, "error"):
                self.log.error(e)
            raise CommunicateException(e)

    def on_recv(self):
        """ recieve request and return reply. """
        protocol = Protocol()
        head_size = protocol.get_head_size()
        head = self.recvall(head_size)
        if len(head) != head_size:
            raise CommunicateException("Connection closed by peer")

        _type, size, codec = protocol.parse_head(head)

        if size > 0 and size < MAX_MESSAGE_LENGTH:
            # print "request size:", size
            body = self.recvall(size)  # raise CommunicateException
            # print "request body", body
            try:
                body = codec.decode(body)
            except Exception, ex:
                e = "Decode Request Message Body Error: %s" % ex
                if hasattr(self.log, "error"):
                    self.log.error(e)
                raise ProtocolException(e)
        else:
            raise CommunicateException("size error: " + str(size))

        if _type == MSG_TYPE_REQUEST:
            if len(body) != 3:
                raise ProtocolException("Request Message Body Content Error")

            # break up the request
            req_id, func_name, params = body

            self.log.info("in %s(%s)" % (func_name, params))

            # get the result for the request
            res = None
            exp = None
            if func_name == "access_agent_is_on_line":
                res = 1
            else:
                try:
                    # imort module
                    mod = __import__(self.call_module_path)
                    components = self.call_module_path.split('.')
                    for comp in components[1:]:
                        mod = getattr(mod, comp)
                    func = getattr(mod, func_name, None)

                    if func is not None:
                        if hasattr(func, "__call__"):
                            try:
                                res = func(*params)
                            except Exception, ex:
                                if hasattr(self.log, "error"):
                                    self.log.error("Error when execute func(%s): %s" % (func_name, ex))
                                raise UserException(str(ex))
                        else:
                            raise NoMethodException("% can not be callable" % func_name)
                    else:
                        raise NoMethodException("No function or attr %s" % func_name)
                except Exception, ex:
                    print ex
                    exp = ex

            # print "reqid, result: ", reqId, res
            self.log.info("out %s(%s)" % (func_name, params))

            if exp is None:
                reply_status = SUCCESS
                reply_msg = res
            else:
                reply_status = AGENT_EXCEPTION
                reply_msg = exp

            reply = Reply(req_id, reply_status, reply_msg)
            msg = protocol.reply_to_raw(reply)
            # print "reply msg: ", msg
            self.sock.sendall(msg)  # CommunicateException
        else:
            if hasattr(self.log, "error"):
                self.log.error("Unknown Message Ignoring...")


if __name__ == '__main__':
    HOST = "127.0.0.1"
    PORT = 5002
    log = logging.getLogger(__name__)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    log.addHandler(ch)
    log.setLevel(logging.DEBUG)

    while True:
        try:
            kiosk = Kiosk(get_kiosk_id(), "kiosk_api", log, HOST, PORT)
            kiosk.run()
        except Exception, ex:
            log.error("error in main: %s" % ex)
            time.sleep(5)
