# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import time

start_time = time.time()


from .version import __version__, ultroid_version
from .custom.init import loop, tasks_db
from .configs import Var
from .startup import *


class ULTConfig:
    lang = "en"
    thumb = "resources/extras/ultroid.jpg"


_ult_cache = {}
_ignore_eval = []

from .custom.init import afterBoot
from .startup._database import udB
from .startup.BaseClient import UltroidClient
from .startup.connections import validate_session, vc_connection
from .startup.funcs import autobot, enable_inline


afterBoot(udB)
BOT_MODE = udB.get_key("BOTMODE")
DUAL_MODE = udB.get_key("DUAL_MODE")

USER_MODE = udB.get_key("USER_MODE")
if USER_MODE:
    DUAL_MODE = False

if BOT_MODE:
    if DUAL_MODE:
        udB.del_key("DUAL_MODE")
        DUAL_MODE = False
    ultroid_bot = None

    if not udB.get_key("BOT_TOKEN"):
        LOGS.critical('"BOT_TOKEN" not Found! Please add it, in order to use "BOTMODE"')
        quit()
else:
    ultroid_bot = UltroidClient(
        validate_session(Var.SESSION, LOGS),
        udB=udB,
        app_version=ultroid_version,
        device_model="Ultroid",
        proxy=udB.get_key("TG_PROXY"),
    )
    ultroid_bot.run_in_loop(autobot())

if USER_MODE:
    asst = ultroid_bot
else:
    asst = UltroidClient(None, bot_token=udB.get_key("BOT_TOKEN"), udB=udB)

if BOT_MODE:
    ultroid_bot = asst
    if udB.get_key("OWNER_ID"):
        try:
            ultroid_bot.me = ultroid_bot.run_in_loop(
                ultroid_bot.get_entity(udB.get_key("OWNER_ID"))
            )
        except Exception as er:
            LOGS.exception(er)
elif not asst.me.bot_inline_placeholder:
    ultroid_bot.run_in_loop(enable_inline(ultroid_bot, asst.me.username))

vcClient = vc_connection(udB, ultroid_bot)


HNDLR = udB.get_key("HNDLR") or "."
DUAL_HNDLR = udB.get_key("DUAL_HNDLR") or "/"
SUDO_HNDLR = udB.get_key("SUDO_HNDLR") or HNDLR

# multidb, version_change, updatenv
del vc_connection, autobot, enable_inline
from .custom.startup_helper import handle_post_startup

handle_post_startup()
