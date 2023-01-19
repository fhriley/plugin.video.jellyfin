import logging

import xbmc

_log_levels = {
    logging.NOTSET: xbmc.LOGNONE,
    # Rather than depending on kodi to turn on debugging globally, use a switch in the settings
    # to turn on debug and log at the LOGINFO level. This makes debugging much easier.
    logging.DEBUG: xbmc.LOGINFO,
    logging.INFO: xbmc.LOGINFO,
    logging.WARNING: xbmc.LOGWARNING,
    logging.ERROR: xbmc.LOGERROR,
    logging.CRITICAL: xbmc.LOGFATAL,
}

LOG_FORMAT = '%(levelname)s|%(name)s|%(filename)s:%(lineno)d|t:%(threadName)s|%(message)s'


class KodiHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        xbmc.log(self.format(record), _log_levels[record.levelno])
