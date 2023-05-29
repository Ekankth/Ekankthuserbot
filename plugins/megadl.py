# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

•{i}megadl <link>
  It Downloads and Upload Files from mega.nz Links.
"""

from os import makedirs
from time import time

from . import (
    HNDLR,
    LOGS,
    bash,
    get_all_files,
    get_string,
    time_formatter,
    ultroid_cmd,
    random_string,
)


@ultroid_cmd(pattern="megadl( (.*)|$)")
async def megadl(e):
    link = e.pattern_match.group(2)
    final_msg = "**Downloaded {total} files in {time}!** \n\n**Directory:** `{dir}`"
    tmp_dir = f"mega/{random_string(8).lower()}"
    makedirs(tmp_dir)
    xx = await e.eor(f"{get_string('com_1')}\nTo Check Progress: `{HNDLR}ls {tmp_dir}`")

    s_time = time()
    x, y = await bash(f"megadl {link} --path {tmp_dir}")
    if y:
        LOGS.warning(y)

    time_taken = time_formatter((time() - s_time) * 1000)
    total_files = len(get_all_files(tmp_dir))
    await xx.reply(final_msg.format(total=total_files, time=time_taken, dir=tmp_dir))
