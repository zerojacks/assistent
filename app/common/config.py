# coding:utf-8
import shutil
import os
import sys
import yaml, yaml_include
from enum import Enum
from lxml import etree as ET
from pathlib import Path
from PyQt5.QtCore import QLocale, QObject, pyqtSignal
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                          OptionsValidator, RangeConfigItem, RangeValidator,
                          FolderListValidator, Theme, FolderValidator, ConfigSerializer, ConfigValidator, __version__)
import logging
from datetime import datetime
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Language(Enum):
    """ Language enumeration """
    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()

class LanguageSerializer(ConfigSerializer):
    """ Language serializer """
    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

class ConfigGroupItem(QObject):
    configChanged = pyqtSignal()

    def __init__(self, group, name):
        super().__init__()
        self.config_items = {}
        self.group = group
        self.name = name

    def add_config_item(self, config_item):
        self.config_items[config_item.key] = config_item
        config_item.valueChanged.connect(self.config_item_changed)

    def config_item_changed(self):
        self.configChanged.emit()

    def reset_to_defaults(self):
        for config_item in self.config_items.values():
            config_item.value = config_item.defaultValue
        self.configChanged.emit()

    def get_config_item(self, key):
        return self.config_items.get(key)

    def serialize(self):
        serialized = {}
        for key, config_item in self.config_items.items():
            serialized[key] = config_item.serialize()
        return serialized

    def deserialize_from(self, serialized):
        for key, value in serialized.items():
            config_item = self.get_config_item(key)
            if config_item:
                config_item.deserializeFrom(value)

    def __str__(self):
        return f'{self.__class__.__name__}[group={self.group}, name={self.name}, config_items={len(self.config_items)}]'

class StringValidator(ConfigValidator):
    def __init__(self, regex_pattern=None):
        self.regex_pattern = regex_pattern

    def validate(self, value):
        if self.regex_pattern:
            import re
            return bool(re.match(self.regex_pattern, value))
        else:
            return True

    def correct(self, value):
        return value

class Config(QConfig):
    """ Config of application """
    # folders
    musicFolders = ConfigItem(
        "Folders", "LocalMusic", [], FolderListValidator())
    logFolder = ConfigItem(
        "Folders", "Log", "app/log", FolderValidator())
    messageFolder = ConfigItem(
        "Folders", "AppInterface", "app/config/appinterface", FolderValidator())
    
    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # Material
    blurRadius = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())
    releaseinfo = ConfigItem("Update", "ReleaseInfo", True, validator=None)

    # Serial configuration
    serial_BaudRate = ConfigItem("Serial", "BaudRate", 9600, OptionsValidator([2400, 4800, 9600, 115200]), restart=False)
    serial_parity = ConfigItem("Serial", "Parity", "偶校验", OptionsValidator(["无校验", "偶校验", "奇校验"]), restart=False)
    serial_databit = ConfigItem("Serial", "DataBits", 8, OptionsValidator([5, 6, 7, 8]), restart=False)
    serial_stopbit = ConfigItem("Serial", "StopBits", 1, OptionsValidator([1, 1.5, 2]), restart=False)

    # TCP Client configuration
    tcpClientIP = ConfigItem("TcpClient", "IP", "127.0.0.1", StringValidator(regex_pattern=r'^(\d{1,3}\.){3}\d{1,3}$'))
    tcpClientPort = ConfigItem("TcpClient", "Port", 1002)

    # TCP Server configuration
    tcpServerIP = ConfigItem("TcpServer", "IP", "127.0.0.1", StringValidator(regex_pattern=r'^(\d{1,3}\.){3}\d{1,3}$'))
    tcpServerPort = ConfigItem("TcpServer", "Port", 1002)

    # MQTT configuration
    mqttip = ConfigItem("Mqtt", "IP", "127.0.0.1", StringValidator(regex_pattern=r'^(\d{1,3}\.){3}\d{1,3}$'))
    mqttport = ConfigItem("Mqtt", "Port", 1883)
    mqttuser = ConfigItem("Mqtt", "user", os.getenv("MQTT_USER", "None"), validator=None)
    mqttpasswd = ConfigItem("Mqtt", "passwd", os.getenv("MQTT_PASSWORD", "None"), validator=None)

    # Basic settings
    ReportReplay = ConfigItem("BasicSeting", "ReportReplay", True, BoolValidator())
    Region = OptionsConfigItem("BasicSeting", "region", "南网", OptionsValidator(["南网", "云南", "广东", "深圳", "广西", "贵州", "海南", "topo"]), restart=False)
    Multireport = ConfigItem("BasicSeting", "Multireport", False, BoolValidator())
    MultireportAdress = ConfigItem("BasicSeting", "MultireportAdress", [], validator=None)
    node_id = ConfigItem("Version", "node_id", "None", validator=None)

    problam_conf = ConfigItem("Problam", "config", [], validator=None)
    
class QframeConfig(QObject):
    """ Config of app """
    appRestartSig = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.file = Path("config/CSG13.xml")
        self._cfg = self
        self.config = None

    def get(self, item):
        """ get the value of config item """
        return item.value

    def load(self, file=None, config=None):
        """ load config """
        if isinstance(config, QConfig):
            self._cfg = config

        if isinstance(file, (str, Path)):
            self._cfg.file = Path(file)
            if self._cfg.file.exists() == False:
                self._cfg.file.parent.mkdir(parents=True, exist_ok=True)
                source_path = Path(f"_internal/{file}")
                try:
                    source_path.replace(self._cfg.file)
                except:
                    self._cfg.file = source_path
        try:
            with open(self._cfg.file, encoding="utf-8") as f:
                self.config = ET.parse(f)
        except:
            self.config = None

    def get_template_item(self, template, protocol, region):
        if self.config is None:
            return None
        root = self.config.getroot()
        def find_template_element(root, target_id, target_protocol, region):
            template_attributes = {
                "id": target_id,
                "protocol": target_protocol,
                "region": region
            }

            # Find the <template> element with the specified attributes
            template_element = None
            for template in root.findall(".//template"):
                if all(template.get(attr) == value for attr, value in template_attributes.items()):
                    template_element = template
                    break

            return template_element
        protocol = protocol.lower()
        target = find_template_element(root, template, protocol, region)
        if target is None:
            protocol = protocol.upper()
            target = find_template_element(root, template, protocol, region)
            if target is None:
                region = "南网"
                protocol = protocol.lower()
                target = find_template_element(root, template, protocol, region)
                if target is None:
                    protocol = protocol.upper()
                    target = find_template_element(root, template, protocol, region)
        return target
    
    def get_item(self, item_id, protocol, region, dir=None):
        def is_vaild_data_item(data_item, target_protocol, tagrget_region, dir=None):
            attri_protocol = data_item.get('protocol')
            if attri_protocol is not None:
                attri_dir = data_item.get('dir')
                if attri_dir is not None and dir is not None:
                    if int(attri_dir) != dir:
                        return False
                protocols = [protocol.upper() for protocol in attri_protocol.split(',')]
                # 判断目标protocol是否在列表中
                target_protocol = target_protocol.upper()
                if target_protocol in protocols:
                    attri_region = data_item.get('region')
                    if attri_region is not None:
                        regions = attri_region.split(',')
                        if tagrget_region in regions:
                            return True
            return False
        def find_target_dataitem(root, target_id, target_protocol, region, dir=None):
            target_node = root.findall(".//*[@id='{}']".format(target_id,target_protocol,region))
            if target_node is None:
                print("No node found with id {} protocol {} and region {}".format(target_id,target_protocol,region))
                return None
            #当前标签无法找到
            print("found with id {} protocol {} and region {}".format(target_id,target_protocol,region))
            for node in target_node:
                if is_vaild_data_item(node, target_protocol, region, dir):
                    return node
                else:
                    parent = node.getparent()
                    while parent is not None:
                        if is_vaild_data_item(parent, target_protocol, region, dir):
                            return node
                        parent = parent.getparent()
            print("No parent found with protocol {} and region {}".format(target_protocol,region))
            return None
        if self.config is None:
            return None
        root = self.config.getroot()
        protocol = protocol.lower()
        target = find_target_dataitem(root, item_id, protocol, region, dir)
        if target is None:
            protocol = protocol.upper()
            target = find_target_dataitem(root, item_id, protocol, region, dir)
            if target is None:
                region = "南网"
                protocol = protocol.lower()
                target = find_target_dataitem(root, item_id, protocol, region, dir)
                if target is None:
                    protocol = protocol.upper()
                    target = find_target_dataitem(root, item_id, protocol, region, dir)
        return target

class LogConfig:
    def __init__(self, log_dir='app/log', log_level=logging.INFO):
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create date-named log folder
        log_folder = os.path.join(log_dir, current_date)
        os.makedirs(log_folder, exist_ok=True)
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        # Create file handler and set format
        log_path = os.path.join(log_folder, 'sys_log.log')
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Create console handler and set format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log_info(self, message, exc_info=True):
        self.logger.info(message, exc_info=exc_info)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message, exc_info=True):
        self.logger.error(message, exc_info=exc_info)

    def log_critical(self, message, exc_info=True):
        self.logger.critical(message, exc_info=exc_info)

    def close(self):
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

class OadFinder:
    def __init__(self, file_path):
        self.data = None
        self.file_path = Path(file_path)
        if self.file_path.exists() == False:
            folder_path = Path('app/config/task_plan')
            source_path = Path("_internal/app/config/task_plan")
            shutil.copytree(source_path, folder_path)

        # Add custom constructor to support !include tag
        folder_path = Path('app/config/task_plan')
        yaml.add_constructor("!inc", yaml_include.Constructor(base_dir=folder_path))

        # Check if file exists and load YAML data
        if not Path(self.file_path).exists():
            print(f"File not found: {file_path}")
            return
        try:
            with open(self.file_path, 'r', encoding="utf-8") as file:
                self.data = yaml.full_load(file)
        except Exception as e:
            log_config.log_error(f"load yaml error: {e}")

    def find_oad_info(self, master_oad_id, virtual_oad_id):
        if not self.data:
            return None
        try:
            for item in self.data:
                if item.get('master_oad_id') == master_oad_id and item.get('virtual_oad_id') == virtual_oad_id:
                    return item
        except Exception as e:
            log_config.log_error(f"find oad info error: {e}")
        return None

class ProtocolInfo:
    PROTOCOL_CSG13 = 'CSG13'
    PROTOCOL_CSG16 = 'CSG16'
    PROTOCOL_DLT64507 = 'DLT/645-2007'

    @property
    def name(self):
        return self.__class__.__name__

class ConfigManager:
    globregion = None
    globalprotocol = None
    thread_local = threading.local()

    @staticmethod
    def _initialize_thread_local():
        if not hasattr(ConfigManager.thread_local, 'config_instances'):
            ConfigManager.thread_local.config_instances = {}

    @staticmethod
    def get_config_xml(data_item_id: str, protocol: str, region: str, dir=None):
        ConfigManager._initialize_thread_local()
        
        if dir is None:
            dir = "app/config"
        
        config_key = f"{protocol}_{region}"
        
        if config_key not in ConfigManager.thread_local.config_instances:
            config_instance = QframeConfig()
            config_file = os.path.join(dir, f"{protocol}.xml")
            config_instance.load(config_file)
            ConfigManager.thread_local.config_instances[config_key] = config_instance
        
        return ConfigManager.thread_local.config_instances[config_key].get_item(data_item_id, protocol, region)

    @staticmethod
    def get_template_element(template:str, protocol:str, region:str, dir=None):
        ConfigManager._initialize_thread_local()
        if dir is None:
            dir = "app/config"
        config_key = f"{protocol}_{region}"
        if config_key not in ConfigManager.thread_local.config_instances:
            config_instance = QframeConfig()
            config_file = os.path.join(dir, f"{protocol}.xml")
            config_instance.load(config_file)
            ConfigManager.thread_local.config_instances[config_key] = config_instance
        return ConfigManager.thread_local.config_instances[config_key].get_template_item(template, protocol, region)

    @staticmethod
    def close_config(self):
        if hasattr(ConfigManager.thread_local, 'config_instances'):
            ConfigManager.thread_local.config_instances.clear()

# Application Constants
YEAR = 2023
AUTHOR = "ZeroJack"
REPO_OWNER = "ZerojackShi"
REPO_NAME = "Assistent"
APP_NAME = "Assistent"
VERSION = "1.2.5"
HELP_URL = "https://www.baidu.com/"
REPO_URL = "https://gitee.com/zerokit/assistent"
RELEASE_URL = "https://gitee.com/zerokit/assistent/releases"
EXAMPLE_URL = "https://www.baidu.com/"
FEEDBACK_URL = "https://www.baidu.com/"
SUPPORT_URL = "https://www.baidu.com/"
CONFIG_DIR = 'app/config'
Authorization = os.getenv("GITHUB_TOKEN", "")
UPDATE_FILE = './upgrade.zip'
UPDATE_DIR = 'upgrade'
APP_EXEC = "Assistent.exe"
WORK_MODE = "debug"

cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load('app/config/config.json', cfg)


config_645 = QframeConfig()
config_645.load('app/config/DLT645.xml')

config_csg13 = QframeConfig()
config_csg13.load('app/config/CSG13.xml')

log_config = LogConfig()

oad_finder = OadFinder('app/config/task_plan/oad_list.yml')