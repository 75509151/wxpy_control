# coding: utf-8
from wxpy import *


bot = Bot(console_qr=True)

# xiaoi = XiaoI('M3LbFZkdlujU', 'CGh8rLT0qpwIxttsmsI9')

tuling = Tuling(api_key='b59d2cb4bdc2452e811b6238bae0f80e')

friends = bot.friends()


@bot.register()
def reply_all_friend(msg):
    if isinstance(msg.chat, Group) and not msg.is_at:
        return
    else:

        tuling.do_reply(msg)


k_g = bot.groups().search("kiosk")
kiosk_g = [] if not k_g else k_g[0]

do_cmd_chats = friends + kiosk_g


@bot.register(do_cmd_chats)
def do_kiosk_cmd(msg):
    if isinstance(msg.chat, Group) and not msg.is_at:
        return
    else:

        tuling.do_reply(msg)


embed()
