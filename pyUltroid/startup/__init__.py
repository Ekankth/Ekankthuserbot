# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from ._logger import (
    LOGS,
    HOSTED_ON,
    TelethonLogger,
    where_hosted,
)

try:
    from safety.tools import *
except ImportError:
    LOGS.error("'safety' package not found!")
