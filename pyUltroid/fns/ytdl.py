# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import glob
import os
import re
import time

from telethon import Button
from yt_dlp import YoutubeDL

from .. import LOGS, udB
from pyUltroid.custom._transfer import pyroUL
from .helper import (
    check_filename,
    download_file,
    humanbytes,
    osremove,
    run_async,
    time_formatter,
)

try:
    from youtubesearchpython import Playlist, VideosSearch
except ImportError:
    Playlist, VideosSearch = None, None


async def ytdl_progress(k, start_time, event):
    if k["status"] == "error":
        return await event.edit("error")
    while k["status"] == "downloading":
        text = (
            f"`Downloading: {k['filename']}\n"
            + f"Total Size: {humanbytes(k['total_bytes'])}\n"
            + f"Downloaded: {humanbytes(k['downloaded_bytes'])}\n"
            + f"Speed: {humanbytes(k['speed'])}/s\n"
            + f"ETA: {time_formatter(k['eta']*1000)}`"
        )
        if round((time.time() - start_time) % 10.0) == 0:
            try:
                await event.edit(text)
            except Exception as ex:
                LOGS.error(f"ytdl_progress: {ex}")


def get_yt_link(query):
    search = VideosSearch(query, limit=1).result()
    try:
        return search["result"][0]["link"]
    except IndexError:
        return


async def download_yt(event, link, ytd):
    find_file = lambda v_id: [
        i
        for i in os.listdir(".")
        if i.startswith(v_id) and not i.endswith((".jpg", ".jpeg", ".png"))
    ]
    reply_to = event.reply_to_msg_id or event
    info = await dler(event, link, ytd, download=True)
    if not info:
        return
    if info.get("_type") == "playlist":
        total = info["playlist_count"]
        for num, file in enumerate(info["entries"]):
            num += 1
            vid_id = file["id"]
            title = file["title"]
            filepath = find_file(vid_id)
            if not filepath:
                return LOGS.warning(f"YTDL ERROR: file not found - {vid_id}")

            if filepath[0].lower().endswith((".part", ".temp")):
                osremove(filepath[0])
                LOGS.warning(
                    f"YTDL Error: {vid_id} - found file ending in .part or .temp"
                )
                await event.respond(
                    f"`[{num}/{total}]` \n`Error: Invalid Video format.\nIgnoring that...`"
                )
                continue

            default_ext = ".mkv" if file.get("height") else ".mp3"
            newpath = check_filename(
                title + (os.path.splitext(filepath[0])[1] or default_ext).lower()
            )
            os.rename(filepath[0], newpath)
            filepath = newpath
            thumb, _ = await download_file(
                file.get("thumbnail", file["thumbnails"][-1]["url"]),
                f"{vid_id}.jpg",
            )
            from_ = info["extractor"].split(":")[0]
            caption = f"`[{num}/{total}]` `{title}`\n\n`from {from_}`"
            ulx = pyroUL(event=event, _path=filepath)
            await ulx.upload(
                thumb=thumb,
                to_delete=True,
                caption=caption,
                auto_edit=False,
                delete_file=True,
                reply_to=reply_to,
            )
        return await event.try_delete()

    # single file
    title = info["title"]
    vid_id = info["id"]
    filepath = find_file(vid_id)
    if not filepath:
        return LOGS.warning(f"YTDL ERROR: file not found - {vid_id}")

    if filepath[0].lower().endswith((".part", ".temp")):
        osremove(filepath[0])
        LOGS.warning(f"YTDL Error: {vid_id} - found file ending in .part or .temp")
        return await event.edit(f"`Error: Invalid format detected...`")

    default_ext = ".mkv" if info.get("height") else ".mp3"
    newpath = check_filename(
        title + (os.path.splitext(filepath[0])[1] or default_ext).lower()
    )
    os.rename(filepath[0], newpath)
    filepath = newpath

    thumb, _ = await download_file(
        info.get("thumbnail", f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"),
        f"{vid_id}.jpg",
    )
    ulx = pyroUL(event=event, _path=filepath)
    await ulx.upload(
        thumb=thumb,
        to_delete=True,
        auto_edit=False,
        reply_to=reply_to,
        delete_file=True,
        caption=f"```{title}```",
    )
    await event.try_delete()


# ---------------YouTube Downloader Inline---------------
# @New-Dev0 @buddhhu @1danish-00


def get_formats(type, id, data):
    if type == "audio":
        audio = []
        for _quality in ("64", "128", "256", "320"):
            _audio = {}
            _audio.update(
                {
                    "ytid": id,
                    "type": "audio",
                    "id": _quality,
                    "quality": _quality + "KBPS",
                }
            )
            audio.append(_audio)
        return audio
    if type == "video":
        video = []
        size = 0
        for vid in data["formats"]:
            if vid["format_id"] == "251":
                size += vid["filesize"] if vid.get("filesize") else 0
            if vid["vcodec"] != "none":
                _id = int(vid["format_id"])
                _quality = str(vid["width"]) + "×" + str(vid["height"])
                _size = size + (vid["filesize"] if vid.get("filesize") else 0)
                _ext = "mkv" if vid["ext"] == "webm" else "mp4"
                if _size < 2147483648:  # Telegram's Limit of 2GB
                    _video = {}
                    _video.update(
                        {
                            "ytid": id,
                            "type": "video",
                            "id": str(_id) + "+251",
                            "quality": _quality,
                            "size": _size,
                            "ext": _ext,
                        }
                    )
                    video.append(_video)
        return video
    return []


def get_buttons(listt):
    id = listt[0]["ytid"]
    butts = [
        Button.inline(
            text=f"[{x['quality']}"
            + (f" {humanbytes(x['size'])}]" if x.get("size") else "]"),
            data=f"ytdownload:{x['type']}:{x['id']}:{x['ytid']}"
            + (f":{x['ext']}" if x.get("ext") else ""),
        )
        for x in listt
    ]
    buttons = list(zip(butts[::2], butts[1::2]))
    if len(butts) % 2 == 1:
        buttons.append((butts[-1],))
    buttons.append([Button.inline("« Back", f"ytdl_back:{id}")])
    return buttons


async def dler(event, url, opts: dict = {}, download=False, info=False):
    await event.edit("`Getting Data...`")
    if "quiet" not in opts:
        opts["quiet"] = True
    opts["username"] = udB.get_key("YT_USERNAME")
    opts["password"] = udB.get_key("YT_PASSWORD")
    opts["logtostderr"] = False
    opts["overwrites"] = True
    opts["geo_bypass"] = True
    opts["prefer_ffmpeg"] = True
    opts["addmetadata"] = True
    if more_opts := udB.get_key("__YTDL_OPTS", force=True):
        if type(more_opts) == dict:
            opts |= more_opts
    if download:
        await ytdownload(url, opts)
    try:
        return await extract_info(url, opts)
    except Exception as e:
        await event.edit(f"{type(e)}: {e}")
        return


@run_async
def ytdownload(url, opts):
    try:
        return YoutubeDL(opts).download([url])
    except Exception as ex:
        LOGS.error(ex)


@run_async
def extract_info(url, opts):
    return YoutubeDL(opts).extract_info(url=url, download=False)


@run_async
def get_videos_link(url):
    to_return = []
    regex = re.search(r"\?list=([(\w+)\-]*)", url)
    if not regex:
        return to_return
    playlist_id = regex.group(1)
    videos = Playlist(playlist_id)
    for vid in videos.videos:
        link = re.search(r"\?v=([(\w+)\-]*)", vid["link"]).group(1)
        to_return.append(f"https://youtube.com/watch?v={link}")
    return to_return
