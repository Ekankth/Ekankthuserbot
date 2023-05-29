# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

•`{i}sample <duration in seconds>`
   Creates Short sample of video..

• `{i}vshots <number of shots>`
   Creates screenshot of video..

• `{i}vtrim <start time> - <end time> in seconds`
    Crop a Lengthy video..
"""

import asyncio
import glob
import os

from pyUltroid.fns.tools import set_attributes
from pyUltroid.custom._transfer import pyroDL, pyroUL

from . import (
    ULTConfig,
    bash,
    duration_s,
    eod,
    genss,
    getFlags,
    get_string,
    mediainfo,
    shq,
    stdr,
    ultroid_cmd,
)


@ultroid_cmd(pattern="sample(?: |$)(.*)")
async def gen_sample(e):
    args = getFlags(e.text, merge_args=True)
    stime = args.kwargs.pop("s", 30)
    vido = await e.get_reply_message()
    msg = await e.eor("`Checking ...`")

    if not vido and bool(args.args):
        if not os.path.exists(args.args[0]):
            return await msg.edit("Path not found")
        path = args.args[0]
        to_del, reply_to = False, e.id

    elif vido and vido.media and "video" in mediainfo(vido.media):
        await msg.edit(get_string("com_1"))
        to_del, reply_to = True, vido.id
        dl = pyroDL(event=msg, source=vido)
        path = await dl.download(_log=False, auto_edit=False, **args.kwargs)
        if isinstance(path, Exception):
            return await msg.edit(f"Error in downloading: `{path}`")
    else:
        return await e.eor(get_string("audiotools_8"), time=5)

    out = os.path.splitext(path)[0] + "_sample.mkv"
    # await asyncio.sleep(1.5)
    await msg.edit(f"Generating Sample of `{stime}` seconds...")
    ss, dd = await duration_s(path, stime)
    cmd = f"ffmpeg -i {shq(path)} -preset ultrafast -ss {ss} -to {dd} -codec copy -map 0 {shq(out)} -y"
    await bash(cmd)
    if to_del:
        os.remove(path)
    x = pyroUL(event=msg, _path=out)
    await x.upload(
        _log=False,
        delete_file=True,
        reply_to=reply_to,
        auto_edit=False,
        caption=f"A Sample Video Of `{stime}` seconds!",
        **args.kwargs,
    )
    await asyncio.sleep(2)
    await msg.delete()


@ultroid_cmd(pattern="vshots(?: |$)(.*)")
async def gen_shots(e):
    args = getFlags(e.text, merge_args=True)
    shot = args.kwargs.pop("s", 5)
    vido = await e.get_reply_message()
    msg = await e.eor("`Checking ...`")

    if not vido and bool(args.args):
        to_del, reply_to = False, e.id
        if not os.path.exists(args.args[0]):
            return await msg.edit("Path not found")
        path = args.args[0]
    elif vido and vido.media and "video" in mediainfo(vido.media):
        await msg.edit(get_string("com_1"))
        to_del, reply_to = True, vido.id
        dl = pyroDL(event=msg, source=vido)
        path = await dl.download(auto_edit=False, _log=False, **args.kwargs)
        if isinstance(path, Exception):
            return await msg.edit(f"Error in downloading: `{path}`")
    else:
        return await msg.edit("Seems Like an Invalid File")

    await msg.edit(f"Generating `{shot}` screenshots...")
    foldr = f"resources/ss/{os.path.basename(path)}"
    if os.path.exists(foldr):
        await bash(f"rm -rf {shq(foldr)}")
    os.makedirs(foldr, exist_ok=True)
    cmd = (
        f"ffmpeg -i {shq(path)} -vf fps=0.009 -vframes {shot} {shq(foldr)}/pic%01d.png"
    )
    await bash(cmd)
    if to_del:
        os.remove(path)
    pic = glob.glob(f"{foldr}/*.png")
    text = f"Uploaded {len(pic)}/{shot} screenshots"
    if not pic:
        text = "`Failed to Take Screenshots..`"
        pic = None
    await e.client.send_message(e.chat_id, text, file=pic, reply_to=reply_to)
    await bash(f"rm -rf {shq(foldr)}")
    await msg.delete()


@ultroid_cmd(pattern="vtrim( (.*)|$)")
async def gen_sample(e):
    sec = e.pattern_match.group(1).strip()
    if not sec or "-" not in sec:
        return await eod(e, get_string("audiotools_3"))
    a, b = sec.split("-")
    if int(a) >= int(b):
        return await eod(e, get_string("audiotools_4"))
    vido = await e.get_reply_message()
    if vido and vido.media and "video" in mediainfo(vido.media):
        msg = await e.eor(get_string("audiotools_5"))
        file, _ = await e.client.fast_downloader(
            vido.document, show_progress=True, event=msg
        )
        file_name = (file.name).split("/")[-1]
        out = file_name.replace(file_name.split(".")[-1], "_trimmed.mkv")
        if int(b) > int(await genss(file.name)):
            os.remove(file.name)
            return await eod(msg, get_string("audiotools_6"))
        ss, dd = stdr(int(a)), stdr(int(b))
        xxx = await msg.edit(f"Trimming Video from `{ss}` to `{dd}`...")
        cmd = f"ffmpeg -i {shq(file.name)} -preset ultrafast -ss {ss} -to {dd} -codec copy -map 0 {shq(out)} -y"
        await bash(cmd)
        os.remove(file.name)
        attributes = await set_attributes(out)
        mmmm, _ = await e.client.fast_uploader(
            out, show_progress=True, event=msg, to_delete=True
        )
        caption = f"Trimmed Video From `{ss}` To `{dd}`"
        await e.client.send_file(
            e.chat_id,
            mmmm,
            thumb=ULTConfig.thumb,
            caption=caption,
            attributes=attributes,
            force_document=False,
            reply_to=e.reply_to_msg_id,
        )
        await xxx.delete()
    else:
        await e.eor(get_string("audiotools_8"), time=5)
