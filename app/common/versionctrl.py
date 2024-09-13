
from .config import VERSION, WORK_MODE

class versionctrl:
    @staticmethod
    def get_version():
        return VERSION
    
    @staticmethod
    def is_release():
        return WORK_MODE == 'release'