import logging

import colorama
import colorlog
from colorama import Fore, Back, Style

colorama.init(autoreset=True)


class ColoredFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        if hasattr(record, 'color'):
            record.msg = f"{record.color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


logg = colorlog.getLogger(__name__)
logg.setLevel(logging.INFO)

handler = colorlog.StreamHandler()
formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
handler.setFormatter(formatter)
logg.addHandler(handler)


# Custom logging methods
def log_user_prompt(prompt):
    logg.info(f"User prompt: {prompt}", extra={'color': Fore.CYAN})


def log_server_response(response):
    logg.info(f"Server response: {response}", extra={'color': Fore.MAGENTA})


def log_context(context):
    logg.info(f"Context: {context}", extra={'color': Fore.YELLOW})
