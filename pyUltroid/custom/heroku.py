# for Heroku ;_;

try:
    import heroku3
except ImportError:
    heroku3 = None

from pyUltroid.startup import LOGS
from pyUltroid.configs import Var


Heroku = {}


def herokuApp():
    if not heroku3:
        Heroku["err"] = "'heroku3' module not installed"
        return LOGS.error(Heroku["err"])

    api_key = Var.HEROKU_API
    app_name = Var.HEROKU_APP_NAME
    if not (api_key and app_name):
        Heroku["err"] = "`HEROKU_API` or `HEROKU_APP_NAME` var is missing"
        return LOGS.error(Heroku["err"])

    try:
        heroku_api = heroku3.from_key(api_key)
        heroku_app = heroku_api.app(app_name)
        Heroku.update(
            {
                "api": heroku_api,
                "app": heroku_app,
                "api_key": api_key,
                "app_name": app_name,
            }
        )
    except Exception as e:
        Heroku["err"] = "Something went wrong. Check your Heroku credentials"
        LOGS.exception(e)
