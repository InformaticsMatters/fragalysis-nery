import os
from logging.config import dictConfig
import yaml

from nery import APP

# Load logger configuration (from cwd)...
# But only if the logging configuration is present!
_LOGGING_CONFIG_FILE = 'logging.yaml'
if os.path.isfile(_LOGGING_CONFIG_FILE):
    _LOGGING_CONFIG = None
    with open(_LOGGING_CONFIG_FILE, 'r') as stream:
        try:
            _LOGGING_CONFIG = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            print(exc)
    dictConfig(_LOGGING_CONFIG)


if __name__ == "__main__":
    APP.run()
