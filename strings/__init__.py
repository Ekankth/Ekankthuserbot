from os import getenv
from glob import glob
from typing import Any, Dict, List, Union

try:
    from yaml import safe_load
except ModuleNotFoundError:
    from pyUltroid.fns.tools import safe_load

from pyUltroid.fns.tools import translate
from pyUltroid import udB, LOGS, ULTConfig


languages = {}
ULTConfig.lang = udB.get_key("language") or getenv("LANGUAGE", "en")


for file in glob("strings/strings/*yml"):
    if file.endswith(".yml"):
        code = file.split("/")[-1].split("\\")[-1][:-4]
        languages[code] = 0


def _load_string(lang):
    path = f"strings/strings/{lang}.yml"
    try:
        with open(path, encoding="UTF-8") as f:
            return safe_load(f)
    except Exception:
        LOGS.exception(f"Error in {lang} language file..")


def get_string(key: str, _res: bool = True) -> Any:
    global languages
    lang = ULTConfig.lang or "en"
    if languages.get(lang) == 0:
        languages[lang] = _load_string(lang)
    try:
        return languages[lang][key]
    except KeyError:
        try:
            en_ = languages["en"][key]
            tr = translate(en_, lang_tgt=lang).replace("\ N", "\n")
            if en_.count("{}") != tr.count("{}"):
                tr = en_
            if languages.get(lang):
                languages[lang][key] = tr
            else:
                languages.update({lang: {key: tr}})
            return tr
        except KeyError:
            if not _res:
                return
            return f"Warning: could not load any string with the key `{key}`"
        except TypeError:
            pass
        except Exception as er:
            LOGS.exception(er)
        if not _res:
            return None
        return languages["en"].get(key) or f"Failed to load language string '{key}'"


def get_help(key):
    doc = get_string(f"help_{key}", _res=False)
    if doc:
        return get_string("cmda") + doc


def get_languages() -> Dict[str, Union[str, List[str]]]:
    out = {}
    for lang in languages.keys():
        data = _load_string(lang)
        lang_info = {
            "name": data["name"],
            "natively": data["natively"],
            "authors": data["authors"],
        }
        out.update({lang: lang_info})
    return out
