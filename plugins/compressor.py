# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}compress <reply to video/path>`
    Available Flags -
    crf: -c=28
    codec: -x264
    speed: -s=superfast
    others: -r > to fix resolution and fps
"""

import asyncio
import math
from os.path import getsize
from pathlib import Path
from re import findall
from time import time

from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageIdInvalidError

from pyUltroid.custom._transfer import pyroDL, pyroUL
from . import (
    LOGS,
    asyncread,
    bash,
    check_filename,
    get_string,
    getFlags,
    humanbytes,
    mediainfo,
    media_info,
    shq,
    time_formatter,
    ultroid_cmd,
    osremove,
)


FFMPEG_CMD = "ffmpeg -hide_banner -loglevel error -progress {progress_file} -i {input_file} -preset {speed} -vcodec {codec} -crf {crf} {other_cmds} {audio_cmd} -c:s copy {output_file} -y"


def fix_resolution(width, height):
    m4 = lambda n: n - (n % 4)
    if width - height >= 0:
        _height = 720  # adjusted for landscape
        if height > _height:
            _div = height / _height
            return m4(round(width / _div)), _height
    _height = 1280
    if height > _height:
        _div = height / _height
        return m4(round(width / _div)), _height


@ultroid_cmd(pattern="compress( (.*)|$)")
async def og_compressor(e):
    args = getFlags(e.text, merge_args=True)
    vido = await e.get_reply_message()
    xxx = await e.eor("Checking...")

    # _ext = "mkv"
    _audio = "-c:a copy"
    codec = "libx264" if "x264" in args.kwargs else "libx265"
    args.kwargs.pop("x264", 0)
    crf = args.kwargs.pop("c", 28 if codec == "libx265" else 34)
    speed = args.kwargs.pop("s", "ultrafast")

    if not vido and bool(args.args):
        path = args.args[0]
        if not Path(path).is_file():
            return await xxx.edit("Path not found")
        _isgif = Path(path).suffix.lower() == ".gif"
        to_delete, reply_to = False, e.id
        o_size = getsize(path)
        await xxx.edit(f"`Found Path {path}\n\nNow Compressing...`")

    elif (vido and vido.media) and any(
        mediainfo(vido.media).startswith(i) for i in ("video", "gif")
    ):
        await xxx.edit(get_string("audiotools_5"))
        dlx = pyroDL(event=xxx, source=vido)
        _isgif = "gif" in mediainfo(vido.media)
        path = await dlx.download(_log=False, auto_edit=False, **args.kwargs)
        if isinstance(path, Exception):
            return await xxx.edit("#Error in downloading file: {path}")
        to_delete, reply_to = True, vido.id
        o_size = getsize(path)
        await xxx.edit(
            f"`Downloaded {path} of {humanbytes(o_size)} in {dlx.dl_time}... \n\nNow Compressing...`"
        )
    else:
        return await xxx.eor(get_string("audiotools_8"), time=8)

    _others = ""
    if _isgif:
        _audio = ""
        codec = "libx264"
    out = check_filename("resources/downloads/" + Path(path).stem + "-compressed.mp4")
    slp_time = 10  # if e.client._bot else 8
    minfo = media_info(path)
    total_frame = minfo.get("frames")
    c_time = time()
    edit_count = 0

    # x, y = await bash(f'''mediainfo --fullscan {shq(path)} | grep "Frame count"''')
    # total_frame = x.split(":")[1].split("\n")[0]
    text = f"`Compressing {Path(out).name} at {crf} CRF` \n"
    progress = check_filename(f"progress-{c_time}.txt")
    Path(progress).touch()

    if args.kwargs.pop("r", 0):
        if total_frame and (total_frame / minfo.get("duration")) > 31:
            _others += "-r 30"
            total_frame = minfo.get("duration") * 30
        if res := fix_resolution(minfo.get("width"), minfo.get("height")):
            _others += f" -vf scale=w={res[0]}:h={res[1]}"

    proce = await asyncio.create_subprocess_shell(
        FFMPEG_CMD.format(
            progress_file=shq(progress),
            input_file=shq(path),
            crf=str(crf),
            output_file=shq(out),
            codec=codec,
            speed=speed,
            audio_cmd=_audio,
            other_cmds=_others,
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Starting Compress!
    while type(proce.returncode) != int:
        speed = 0
        await asyncio.sleep(slp_time)
        filetext = await asyncread(progress)
        with open(progress, "a") as f:
            f.truncate(300)
        frames = findall("frame=(\\d+)", filetext)
        size = findall("total_size=(\\d+)", filetext)

        size = int(size[-1]) if size else 0
        elapse = int(frames[-1]) if frames else 0
        e_size = f"**Done ~**  `{humanbytes(size)}` \n"
        del filetext, size

        if total_frame and elapse:
            per = elapse * 100 / total_frame
            time_diff = time() - c_time
            speed = round(elapse / time_diff, 2)
            if int(speed) != 0:
                some_eta = ((total_frame - elapse) / speed) * 1000
                progress_str = "`[{0}{1}] {2}%` \n\n".format(
                    "".join("●" for i in range(math.floor(per / 5))),
                    "".join("" for i in range(20 - math.floor(per / 5))),
                    round(per, 2),
                )
                eta = f"**ETA ~**  `{time_formatter(some_eta)}`"
                p_text = text + progress_str + e_size + eta
        else:
            edit_count += slp_time
            p_text = (
                f"{text}\n` ~ Missing Frame Count..` \n\n"
                f"{e_size}**Elapsed ~**  `{time_formatter(edit_count * 1000)}`"
            )
            slp_time = 15

        if int(speed) > 0 or edit_count > 0:
            try:
                await xxx.edit(p_text)
            except MessageNotModifiedError:
                LOGS.debug("Compressor msg edit err..", exc_info=True)
            except MessageIdInvalidError:
                await asyncio.sleep(3)
                try:
                    proce.kill()
                except:
                    pass
                await asyncio.sleep(6)
                osremove(progress, out)
                if to_delete:
                    osremove(path)
                return LOGS.debug(f"cancelled compression of: {path}")

    # Uploader
    if to_delete:
        osremove(path)
    osremove(progress)
    difff = time_formatter((time() - c_time) * 1000)

    minfo = media_info(out)
    if minfo.get("type") == "video" and not minfo.get("has_audio"):
        o_path = Path(out)
        out = check_filename(str(o_path.with_suffix(".mkv")))
        o_path.rename(out)

    c_size = getsize(out)
    await xxx.edit(
        f"`Compressed {humanbytes(o_size)} to {humanbytes(c_size)} in {difff}\nTrying to Upload...`"
    )
    differ = 100 - ((c_size / o_size) * 100)

    edtext = f"{minfo.get('height')}p"
    if frames := minfo.get("frames"):
        edtext += f"@{round(frames / minfo.get('duration'))}fps"
    caption = (
        f"**Compressed from** `{humanbytes(o_size)}` **to** `{humanbytes(c_size)}` **in** `{difff}`"
        f"\n\n**Codec:** `{codec}` • `{edtext}`\n"
        f"**Compression Ratio:** `{differ:.2f}%`"
    )
    x = pyroUL(event=xxx, _path=out)
    await x.upload(
        caption=caption,
        delete_file=True,
        reply_to=reply_to,
        _log=False,
        **args.kwargs,
    )
