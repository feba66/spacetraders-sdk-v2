import os
import logging
import threading



class SpaceTradersLogger:
    # region variables
    name: str
    logger: logging.Logger
    formatter:logging.Formatter
    # endregion

    def __init__(self,name="st-logger") -> None:
        # region inits
        self.name=name
        self.logger = logging.getLogger(f"{name}-{threading.current_thread().name}")
        self.formatter = logging.Formatter("%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s")
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.DEBUG)

            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            fh = logging.FileHandler(f"{os.getenv('WORKING_FOLDER')}{name}.log", encoding="utf-8")

            fh.setLevel(logging.DEBUG)

            ch.setFormatter(self.formatter)
            fh.setFormatter(self.formatter)

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
        # endregion
    def debug(self,msg: object):
        self.logger.debug(msg)
    def info(self,msg: object):
        self.logger.info(msg)
    def warn(self,msg: object,*args: object):
        self.logger.warn(msg,args)
    def error(self,msg: object,*args: object):
        self.logger.error(msg,args)
    def fatal(self,msg: object,*args: object):
        self.logger.fatal(msg,args)