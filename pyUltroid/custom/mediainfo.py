# better mediainfo!

from os.path import getsize
from re import findall
from shlex import quote, split
from subprocess import run

from pymediainfo import MediaInfo

from pyUltroid.fns.helper import humanbytes
from pyUltroid.startup import LOGS


def _parser(data, attr, to_int=True):
    def _conv_to_int(n):
        try:
            return round(float(n)) if n else 0
        except ValueError:
            return 0

    out = getattr(data, attr, 0)
    if to_int and type(out) != int:
        out = _conv_to_int(out)
    return out


class TGMediaInfo:
    def __init__(self, path):
        try:
            self.path = path
            self.obj = MediaInfo.parse(self.path)
            self.general_track = self.obj.general_tracks[0]
        except FileNotFoundError:
            return "File doesn't exist on Server.."
        except (RuntimeError, IndexError, Exception) as exc:
            LOGS.exception(exc)
            return "MediaInfo failed to Parse the File."

    # de facto init
    def __call__(self):
        out = {}
        out["size"] = humanbytes(getsize(self.path))
        _ext = _parser(self.general_track, "file_extension", 0)
        if _ext and _ext.lower() in ("tgs", "webp"):
            out["type"] = "sticker"
            return out

        minfo = {}
        if data := self.obj.video_tracks:
            self.track = data[0]
            minfo = self.video_info()
        elif data := self.obj.audio_tracks:
            self.track = data[0]
            minfo = self.audio_info()
        elif data := self.obj.image_tracks:
            self.track = data[0]
            minfo = self.image_info()
        else:
            out["type"] = "document"
        return out | minfo

    # audio stream helper.
    @staticmethod
    def _get_audio_metadata(data):
        result = {"title": "Unknown Track", "artist": "Unknown Artist"}
        _items = {
            "title": ("title", "track_name", "file_name_extension"),
            "artist": ("performer", "album"),
        }
        for key, vars in _items.items():
            for attr in vars:
                if value := _parser(data, attr, 0):
                    result.update({key: value})
                    break
        return tuple(result.values())

    # alternate method for getting frame count from video stream.
    @staticmethod
    def _get_frame_count(file):
        cmd = f"ffprobe -hide_banner -v error -select_streams v:0 -show_entries stream=nb_read_packets -of default=noprint_wrappers=1 {quote(file)}"
        # -count_frames > slow
        try:
            res = run(split(cmd), capture_output=True, text=True)
            if res.returncode == 0:
                if frame := findall("[\d\.]+", res.stdout):
                    return int(frame[0])
        except Exception:
            LOGS.exception(f"error in getting frame count via ffprobe: {file}")

    # alternate method for getting bitrate from video stream.
    @staticmethod
    def _get_bitrate(file):
        cmd = f"ffprobe -hide_banner -v error -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1 {quote(file)}"
        try:
            res = run(split(cmd), capture_output=True, text=True)
            if res.returncode == 0:
                if b_rate := findall("[\d\.]+", res.stdout):
                    return int(frame[0])
        except Exception:
            LOGS.exception(f"error in getting bitrate via ffprobe: {file}")

    # alternate method for getting duration from video or audio stream.
    @staticmethod
    def _get_duration(file):
        cmd = f"ffprobe -hide_banner -v error -show_entries format=duration -of default=noprint_wrappers=1 {quote(file)}"
        try:
            res = run(split(cmd), capture_output=True, text=True)
            _dur = findall("[\d\.]+", res.stdout) if res.returncode == 0 else None
            return round(float(_dur[0])) if _dur else 0
        except Exception:
            LOGS.exception(f"error in getting duration via ffprobe: {file}")
            return 0

    # video stream helper.
    def _video_stream_helper(self, data):
        # webm sticker
        if (
            self.general_track.format.lower() == "webm"
            and data.get("duration") <= 3
            and data.get("width") == 512
        ):
            data["type"] = "sticker"

        # recheck frame count
        if not data.get("frames"):
            if frames := self._get_frame_count(self.path):
                data["frames"] = frames

        # recheck bitrate
        if not data.get("bitrate"):
            if b_rate := self._get_bitrate(self.path):
                data["bitrate"] = b_rate

        # gif check
        format = _parser(self.track, "format", 0)
        if format and format.lower() == "gif":
            data["type"] = "gif"
        return data

    # video stream
    def video_info(self):
        _dur = round(_parser(self.track, "duration") / 1000)
        duration = _dur or self._get_duration(self.path)
        out = {
            "type": "video",
            "duration": duration,
            "has_audio": bool(self.obj.audio_tracks),
            "width": _parser(self.track, "width"),
            "height": _parser(self.track, "height"),
            "bitrate": _parser(self.track, "bit_rate"),
            "frames": _parser(self.track, "frame_count"),
        }
        return self._video_stream_helper(out)

    # image stream
    def image_info(self):
        out = {
            "type": "image",
            "width": _parser(self.track, "width"),
            "height": _parser(self.track, "height"),
        }
        format = _parser(self.track, "format", 0)
        if format and format.lower() == "gif":
            return self.video_info()
        return out

    # audio stream
    def audio_info(self):
        _dur = round(_parser(self.general_track, "duration") / 1000)
        duration = _dur or self._get_duration(self.path)
        title, artist = self._get_audio_metadata(self.general_track)
        return {
            "type": "audio",
            "duration": duration,
            "title": title,
            "artist": artist,
            "performer": artist,
        }


def media_info(file):
    minfo = TGMediaInfo(file)
    out = minfo()
    return out
