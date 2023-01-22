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


class LogHolder:
    _holders = []

    @classmethod
    def getLogger(cls, name):
        holder = LogHolder(name)
        cls._holders.append(holder)
        return holder

    @classmethod
    def update_all(cls):
        for holder in cls._holders:
            holder.update()

    def __init__(self, name):
        self._name = name
        self._log = None
        self.update()

    def update(self):
        self._log = logging.getLogger(self._name)

    @property
    def log(self):
        return self._log
