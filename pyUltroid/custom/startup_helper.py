from pyUltroid import udB
from pyUltroid.startup import LOGS
from pyUltroid.startup.funcs import _version_changes, update_envs
from .multi_db import _init_multi_dbs


def handle_post_startup():
    update_envs()
    _version_changes(udB)
    _init_multi_dbs("MULTI_DB")
