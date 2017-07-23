#!/usr/bin/python
# coding: utf-8
""" The ssh tunnel and ssh reverse tunnel.
    相关命令
    ssh-keygen
    ssh-copy-id 可以直接将本地的公钥拷贝到服务器
    ssh 反向连接 不稳定，所有才有了这个脚本，实际上可以使用autossh代替此脚本

"""

__VERSION__ = '0.10'

# speed up
try:
    import psyco
    psyco.full()
except:
    pass

import os
import time
import pexpect
import logging
from .kiosk_info import get_kiosk_id

# Config for cka.
MAX_DUP = 120
TUNNEL_INTERVAL = 30


DEBUG = 0
INFO = 1
ERROR = 2


DEFAULT_ID = "A010"
TUNNEL_SERVER = '45.63.87.142'
TUNNEL_USER = "jay"
LOCAL_PORT = 5002
PEM_FILE_PATH = os.path.join("/home/mm", "var", "config", "parking_key")


# init log
log = logging.getLogger(__name__)

# 再创建一个handler，用于输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)
log.setLevel(logging.DEBUG)

log.info("MKA VERSION: %s" % __VERSION__)
log.info("server : %s" % TUNNEL_SERVER)


class Cka(object):

    def __init__(self, cka_type):
        """ init """
        self.hostname = get_kiosk_id()
        # the type is 1 or 2, 1 as ssh tunnel, 2 as ssh reverse tunnel
        self._type = cka_type
        # the last log information recorded
        self.last_text = ""
        # duplicate count of log information, if it is reached MAX_DUP, log it
        self.current_dup = 0
        # get the ssh tunnel command
        self.cmd = self.get_cmd()
        log.info("cmd : %s " % self.cmd)
        self.tunnel = None
        self.reset_file = ""
        self.alive_file = ""

    def open_tunnel(self):
        """ open tunnel """
        try:
            # Remove the .ssh/known_hosts
            try:
                os.remove('%s/.ssh/known_hosts' % os.environ['HOME'])
            except:
                pass
            log.debug("[open]enter open_tunnel func")

            self.kill_tunnel()

            if not self.cmd:
                log.error("[open]can not get the cmd")
                return False

            # log.info("cmd: %s" % self.cmd)
            self.tunnel = pexpect.spawn(self.cmd)

            """
            # for debug
            try:
                self.tunnel.setlog(sys.stdout)
            except:
                self.tunnel.logfile = sys.stdout
            """

            index = self.tunnel.expect([pexpect.TIMEOUT, '[%s|mm|master]@.*' % TUNNEL_USER, 'forwarding', "RSA key", "yes"])

            if index == 3 or index == 4:  # 'first login', add into known_hosts
                self.tunnel.sendline("yes\n")
                time.sleep(0.1)
                index = self.tunnel.expect([pexpect.TIMEOUT, '[%s|mm|master]@.*' % TUNNEL_USER, 'forwarding'])

            if index == 1:  # open tunnel successfully
                return True
            elif index == 2:  # other tunnels may be opened
                self.kill_tunnel()
                log.info("[open]remote forwarding deny!")
                return False
            else:  # timeout or something
                self.kill_tunnel()
                log.info('[open]login timeout')
                return False
        except Exception, ex:
            self.kill_tunnel()
            log.info('open_tunnel exception: %s' % ex)
            time.sleep(0.5)
            return False

    def check_tunnel(self):
        """ Check if the tunnel is alive.
        """

        if not self.tunnel:
            # the tunnel has not open
            return False

        if not self.tunnel.isalive():
            log.info('[check](re)open tunnel failed')
            return False

        # clear some obstruct
        self.tunnel.sendline("\n")
        index = self.tunnel.expect([pexpect.TIMEOUT, '\$'])
        if index == 0:  # timeout
            return False

        # Check if it is alive, 5 times.
        RETRY_TIME = 5
        for i in range(RETRY_TIME):
            time.sleep(1)
            self.tunnel.sendline("rm %s\r\n" % self.reset_file)
            index = self.tunnel.expect([pexpect.TIMEOUT, '\$'])

            if index == 0:  # timeout
                log.info("[check]send rm command, but wait timeout, "
                         "reset tunnel")
                return False
            elif index == 1:
                pass

            try:
                result = self.tunnel.read_nonblocking(8192, 10)
                print result
                if result.find('No such file or directory') != -1:
                    #log.info('tunnel checking ok, sleeping\n', INFO)
                    pass
                elif result.count(self.reset_file) == 1:
                    log.debug("[check]reset command:%s" % repr(result))
                    log.info("[check]recv reboot command, reset tunnel, "
                             "time %s" % (i + 1))
                    if i < RETRY_TIME - 1:
                        continue
                    log.info("[check]recv reboot command, reset tunnel")
                    self.kill_tunnel()
                    return False
                else:
                    log.debug("[check]unexcept: %s\n" % repr(result))

                self.tunnel.sendline("touch %s\n" % self.alive_file)
                break
            except Exception, ex:
                log.error("[check]error: %s, reset tunnel" % ex)
                self.kill_tunnel()
                return False

        log.info("[check]checking tunnel OK")
        return True

    def close_tunnel(self):
        """ Close the tunnel.
        """
        try:
            if hasattr(self.tunnel, "close"):
                self.tunnel.close()
            self.tunnel = None
        except Exception, ex:
            log.error("[close] error: %s" % ex)

    def kill_tunnel(self):
        """ Kill the tunnel. """
        pass

    def hostname2port(self, prefix=2):
        """ Get the port according to hostname, the kiosk is allowed from A000
        to J999.
        e.g. A000 ==> 21000
        @param prefix(int): the prefix digit for the
        @return: the port converted from the hostname
        @rtype: string
        """
        port = chr(ord(self.hostname[-4]) - 0x10)  # cover A to 1, B to 2, etc
        # check if the port is valid, 0 is as default
        if not port.isdigit():
            port = "0"
        port += self.hostname[-3:]

        return str(prefix) + port

    def get_cmd(self):
        """ Get linux command of cka or cka2. """
        return ""


class Cka1(Cka):

    def __init__(self):
        """ Reverse ssh """
        super(Cka1, self).__init__(cka_type=1)
        self.reset_file = 'reset/%s' % self.hostname
        self.alive_file = 'online/%s' % self.hostname

    def get_cmd(self):
        """ Get linux command. """
        # return "/usr/bin/ssh -i %s -R %s:localhost:22 " \
        #        "-R %s:localhost:5001 %s@%s" % (PEM_FILE_PATH,
        #                                        self.hostname2port(2),
        #                                        self.hostname2port(1),
        #                                        TUNNEL_USER,
        #                                        G_TUNNEL_SERVER)
        return "ssh  -R %s:localhost:22 " \
               "-R %s:localhost:%s %s@%s" % (
                   self.hostname2port(2),
                   self.hostname2port(1),
                   LOCAL_PORT,
                   TUNNEL_USER,
                   TUNNEL_SERVER)

    def kill_tunnel(self):
        """ Kill the tunnel. """
        log.debug("kill tunnel")
        try:
            os.system('pkill -9 -f "ssh -i %s -R"' % PEM_FILE_PATH)
            self.close_tunnel()
        except Exception, ex:
            log.info("[killer]kill failed: %s" % str(ex))


def maintain_tunnel():
    """ maintain the two ssh tunnels
    """
    try:
        import stat
        os.chmod(PEM_FILE_PATH, stat.S_IRUSR)
    except Exception, ex:
        log.warning("change pem file permission error: %s" % ex)
    cka1 = Cka1()
    # cka2 = Cka2()

    while True:
        log.debug("[maintain](re)open tunnel")
        try:
            # open tunnel for cka1
            if not cka1.check_tunnel():
                cka1.open_tunnel()
            # open tunnel for cka2
            # if not cka2.check_tunnel():
            #     cka2.open_tunnel()

            # maintain the tunnels
            while True:
                # check the tunnels, if cka1 is down, break
                if not cka1.check_tunnel():
                    break
                time.sleep(TUNNEL_INTERVAL)
        except Exception, ex:
            log.error("[maintain] error: %s" % ex)


if __name__ == "__main__":
    maintain_tunnel()
