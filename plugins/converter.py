# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_converter")

import os
import time

from . import LOGS

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image
except ImportError:
    LOGS.info(f"{__file__}: PIL  not Installed.")
    Image = None

from telegraph import upload_file as uf

from pyUltroid.custom._transfer import pyroDL, pyroUL
from . import (
    ULTConfig,
    asyncwrite,
    bash,
    check_filename,
    con,
    downloader,
    get_paste,
    get_string,
    getFlags,
    shq,
    udB,
    ultroid_cmd,
    uploader,
)

opn = []


@ultroid_cmd(
    pattern="thumbnail$",
)
async def _(e):
    r = await e.get_reply_message()
    if r.photo:
        dl = await r.download_media()
    elif r.document and r.document.thumbs:
        dl = await r.download_media(thumb=-1)
    else:
        return await e.eor("`Reply to Photo or media with thumb...`")
    variable = uf(dl)
    os.remove(dl)
    nn = f"https://graph.org{variable[0]}"
    udB.set_key("CUSTOM_THUMBNAIL", str(nn))
    await bash(f"wget {nn} -O resources/extras/ultroid.jpg")
    await e.eor(get_string("cvt_6").format(nn), link_preview=False)


@ultroid_cmd(
    pattern="rename( (.*)|$)",
)
async def imak(event):
    reply = await event.get_reply_message()
    if not (reply and reply.media):
        return await event.eor(get_string("cvt_1"))
    args = getFlags(event.text, merge_args=True)
    if not bool(args.args):
        return await event.eor(get_string("cvt_2"))
    xx = await event.eor(get_string("com_1"))
    inp = args.args[0]
    if reply.media:
        if hasattr(reply.media, "document"):
            dl = pyroDL(event=xx, source=reply)
            file = await dl.download(auto_edit=False, _log=False, **args.kwargs)
            if isinstance(file, Exception):
                return await xx.edit(f"**Error while downloading** \n`{file}`")
        else:
            file = await event.client.download_media(reply.media)

    inp = check_filename(inp)
    await bash(f"mv {shq(file)} {shq(inp)}")
    if not os.path.exists(inp) or (os.path.exists(inp) and not os.path.getsize(inp)):
        os.rename(file, inp)
    ul = pyroUL(event=xx, _path=inp)
    await ul.upload(
        delete_file=True,
        reply_to=reply.id,
        auto_edit=False,
        _log=False,
        **args.kwargs,
    )
    await xx.delete()


conv_keys = {
    "img": "png",
    "sticker": "webp",
    "webp": "webp",
    "image": "png",
    "webm": "webm",
    "gif": "gif",
    "json": "json",
    "tgs": "tgs",
}


@ultroid_cmd(
    pattern="convert( (.*)|$)",
)
async def uconverter(event):
    xx = await event.eor(get_string("com_1"))
    a = await event.get_reply_message()
    if a is None:
        return await event.eor("`Reply to Photo or media with thumb...`")
    input_ = event.pattern_match.group(1).strip()
    b = await a.download_media("resources/downloads/")
    if not b and (a.document and a.document.thumbs):
        b = await a.download_media(thumb=-1)
    if not b:
        return await xx.edit(get_string("cvt_3"))
    try:
        convert = conv_keys[input_]
    except KeyError:
        return await xx.edit(get_string("sts_3").format("gif/img/sticker/webm"))
    file = await con.convert(b, outname="ultroid", convert_to=convert)
    if file:
        await event.client.send_file(
            event.chat_id, file, reply_to=event.reply_to_msg_id or event.id
        )
        os.remove(file)
    await xx.delete()


@ultroid_cmd(
    pattern="doc( (.*)|$)",
)
async def _(event):
    input_str = event.pattern_match.group(1).strip()
    if not (input_str and event.is_reply):
        return await event.eor(get_string("cvt_1"), time=5)
    xx = await event.eor(get_string("com_1"))
    a = await event.get_reply_message()
    if not a.message:
        return await xx.edit(get_string("ex_1"))
    input_str = check_filename(input_str)
    await xx.edit(f"**Packing into** `{input_str}`")
    await asyncwrite(input_str, str(a.message), mode="w")
    await event.client.send_file(
        event.chat_id,
        file=input_str,
        thumb=ULTConfig.thumb,
        reply_to=event.reply_to_msg_id,
    )
    os.remove(input_str)
    await xx.delete()


@ultroid_cmd(
    pattern="open( (.*)|$)",
)
async def _(event):
    a = await event.get_reply_message()
    b = event.pattern_match.group(1).strip()
    if not ((a and a.media) or (b and os.path.exists(b))):
        return await event.eor(get_string("cvt_7"), time=5)
    xx = await event.eor(get_string("com_1"))
    rem = None
    if not b:
        b = await a.download_media()
        rem = True
    try:
        with open(b) as c:
            d = c.read()
    except UnicodeDecodeError:
        return await xx.eor(get_string("cvt_8"), time=5)
    try:
        await xx.edit(f"```{d}```")
    except BaseException:
        what, key = await get_paste(d)
        await xx.edit(
            f"**MESSAGE EXCEEDS TELEGRAM LIMITS**\n\nSo Pasted It On [SPACEBIN](https://spaceb.in/{key})"
        )
    if rem:
        os.remove(b)
