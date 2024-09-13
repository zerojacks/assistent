from PyQt5.QtCore import Qt, QEasingCurve,pyqtSignal,QSize
from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy,QFormLayout
from qfluentwidgets import (Pivot, qrouter, SegmentedWidget, TextEdit, CheckBox, ComboBox,
                            TabCloseButtonDisplayMode, RadioButton, LineEdit,InfoBarPosition,InfoBar,PrimaryPushButton,PlainTextEdit)
from PyQt5.QtGui import QFont, QResizeEvent
from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from ..plugins.frame_csg import add_point_to_frame,calculate_measurement_points
from ..plugins import protocol
from ..plugins.frame_fun import FrameFun as frame_fun
from .analysic_interface import CustomTreeWidgetItem,CustomTreeWidget
from ..common.config import cfg, ProtocolInfo,ConfigManager
from ..common.versionctrl import versionctrl
from ..common.signal_bus import signalBus
from ..plugins.MeterTask import MeterTask
from ..plugins.custom_frame import custom_frame
from PyQt5.QtCore import QDateTime
from datetime import datetime
import pytz

class ReadTask(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.item_position = {}

        self.taskParamlayout = QHBoxLayout()  # 使用水平布局
        self.taskParamlabel = QLabel('任务内容')
        self.taskParamInput = PlainTextEdit()
        self.taskParamButton = PrimaryPushButton(self.tr('确定'))
        self.taskParamlayout.addWidget(self.taskParamlabel)
        self.taskParamlayout.addSpacing(5)
        self.taskParamlayout.addWidget(self.taskParamInput)
        self.taskParamlayout.addSpacing(5)
        self.taskParamlayout.addWidget(self.taskParamButton)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.taskParamInput.setSizePolicy(size_policy)

        self.tree_widget = CustomTreeWidget()
        self.qvlayout = QVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.taskParamlayout)
        self.qvlayout.addSpacing(5)
        self.qvlayout.addWidget(self.tree_widget, 8)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_widget.setSizePolicy(size_policy)
        self.qvlayout.setContentsMargins(0, 0, 0, 0)

        self.taskParamButton.clicked.connect(self.taskParamButtonClicked)
    def taskParamButtonClicked(self):
        data = self.taskParamInput.toPlainText()
        alalysic_result = []
        self.tree_widget.clear()
        self.tree_widget.last_item = None
        if data == '':
            InfoBar.warning(
            title=self.tr('告警'),
            content=self.tr("数据内容不能为空"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
            return
        cleaned_string = data.replace(' ', '').replace('\n', '')
        data_content = [int(cleaned_string[i:i + 2], 16) for i in range(0, len(cleaned_string), 2)]
        item_str = frame_fun.to_hex_string_with_space(data_content)
        self.taskParamInput.setPlainText(item_str.upper())
        protocol.frame_fun.globregion = cfg.get(cfg.Region)
        meter_task = MeterTask()
        meter_task.analysic_meter_task(data_content, alalysic_result, 0)
        self.tree_widget.create_tree(None, alalysic_result, self.item_position)
        self.tree_widget.expandAll()

class CustomItem(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.item_position = {}

        self.itemlabel = QLabel('数据标识')
        self.itemInput = TextEdit()
        self.itemlayout = QHBoxLayout()
        # self.itemlabel.setAlignment(Qt.AlignLeft)
        self.itemInput.setAlignment(Qt.AlignLeft)
        self.itemlayout.addWidget(self.itemlabel)
        self.itemlayout.addSpacing(5)
        self.itemlayout.addWidget(self.itemInput, 1 ,Qt.AlignLeft)
        self.itemInput.setFixedSize(200,35)

        self.contentlabel = QLabel('数据内容')
        self.contentInput = PlainTextEdit()
        self.contentlayout = QHBoxLayout()  # 使用水平布局
        self.contentlayout.addWidget(self.contentlabel)
        self.contentlayout.addSpacing(5)
        self.contentlayout.addWidget(self.contentInput)

        self.Button = PrimaryPushButton(self.tr('解析'))
        self.Button.setFixedWidth(100)

        self.infolayout = QVBoxLayout()
        self.infolayout.addLayout(self.itemlayout)
        self.infolayout.addSpacing(5)
        self.infolayout.addLayout(self.contentlayout)
        self.infolayout.addSpacing(5)
        self.infolayout.addWidget(self.Button,1 ,Qt.AlignCenter)

        self.tree_widget = CustomTreeWidget()
        self.qvlayout = QVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.infolayout)
        self.qvlayout.addSpacing(5)
        self.qvlayout.addWidget(self.tree_widget, 8)
        # size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.tree_widget.setSizePolicy(size_policy)
        self.qvlayout.setContentsMargins(0, 0, 0, 0)

        self.Button.clicked.connect(self.taskParamButtonClicked)
    def taskParamButtonClicked(self):
        try:
            item = self.itemInput.toPlainText()
            data = self.contentInput.toPlainText()
            alalysic_result = []
            self.tree_widget.clear()
            self.tree_widget.last_item = None
            if item == '':
                InfoBar.warning(
                title=self.tr('告警'),
                content=self.tr("数据标识不能为空"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
                return
            if data == '':
                InfoBar.warning(
                title=self.tr('告警'),
                content=self.tr("数据内容不能为空"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
                return
            cleaned_string = data.replace(' ', '').replace('\n', '')
            data_content = [int(cleaned_string[i:i + 2], 16) for i in range(0, len(cleaned_string), 2)]
            protocol.frame_fun.globregion = cfg.get(cfg.Region)
            template_element = ConfigManager.get_config_xml(item, ProtocolInfo.PROTOCOL_CSG13.name(),frame_fun.globregion)
            if template_element is None:
                InfoBar.warning(
                title=self.tr('告警'),
                content=self.tr("数据标识不存在"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
                return
            show_data = protocol.parse_data_item(template_element, data_content, 0, 0, ProtocolInfo.PROTOCOL_CSG13.name())
            frame_fun.prase_data_with_config(show_data, False, alalysic_result)
            sub_result = []
            reverse_item = item.replace(' ', '').replace('\n', '')
            item_list = [int(reverse_item[i:i + 2], 16) for i in range(0, len(reverse_item), 2)]
            item_str = frame_fun.to_hex_string_reverse_with_space(item_list)
            name = template_element.find('name').text
            dis_data_identifier = "数据标识编码：" + f"[{reverse_item.upper()}]" + "-" + name
            result_str = f"数据标识[{reverse_item.upper()}]数据内容：" + frame_fun.get_data_str_reverser(data_content)
            frame_fun.add_data(sub_result, f"数据标识编码DI",item_str,dis_data_identifier,[])
            frame_fun.add_data(sub_result, f"数据标识内容",frame_fun.get_data_str_with_space(data_content),result_str,[],alalysic_result)
            self.tree_widget.create_tree(None, sub_result, self.item_position)
            self.tree_widget.expandAll()
        except Exception as e:
            print(e)
            InfoBar.error(
                title=self.tr('错误'),
                content=self.tr("解析失败"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

class DaTools(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)    

        self.itemlayout = QHBoxLayout(self)
        self.itemlayout.setContentsMargins(0, 0, 0, 0)

        self.contentInput = LineEdit()
        self.contentInput.setPlaceholderText(self.tr("请输入测量点"))

        self.daInput = LineEdit()
        self.daInput.setPlaceholderText(self.tr("请输入DA"))

        self.contentInput.textChanged.connect(self.contentInputTextChanged)
        self.daInput.textChanged.connect(self.daInputTextChanged)

        self.itemlayout.addWidget(self.contentInput)
        self.itemlayout.addWidget(self.daInput)

    def contentInputTextChanged(self):
        text = self.contentInput.text()
        data = []
        if text == '':
            self.daInput.setPlaceholderText(self.tr("请输入DA"))
            return
        try:
            point = int(text, 16)
            add_point_to_frame(point, data)
            self.daInput.textChanged.disconnect(self.daInputTextChanged)
            self.daInput.setText(frame_fun.get_data_str_with_space(data))
            self.daInput.textChanged.connect(self.daInputTextChanged)
        except Exception as e:
            pass

    def daInputTextChanged(self):
        text = self.daInput.text()
        if text == '':
            return
        try:
            data_list = frame_fun.get_frame_list_from_str(text).copy()
            total_measurement_points, measurement_points_array = calculate_measurement_points(data_list)
            if total_measurement_points == 1 and measurement_points_array[0] == 0xffff:
                text = "FFFF"
            else:
                text = ",".join([str(i) for i in measurement_points_array])

            self.contentInput.textChanged.disconnect(self.contentInputTextChanged)
            self.contentInput.setText(text)
            self.contentInput.textChanged.connect(self.contentInputTextChanged)
        except Exception as e:
            print(e)

class TimestampConverter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Timestamp Converter')

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Timestamp to Time conversion
        stamplayout = QHBoxLayout()
        self.timestamp_input = LineEdit(self)
        self.timestamp_input.setPlaceholderText('输入时间戳 (秒或毫秒)')
        self.timestamp_input.textChanged.connect(self.convert_to_time)
        self.millisecs_radiobtn = RadioButton('毫秒')
        self.seconds_radiobtn = RadioButton('秒')
        self.seconds_radiobtn.setChecked(True)
        stamplayout.addWidget(self.timestamp_input)
        stamplayout.addWidget(self.millisecs_radiobtn)
        stamplayout.addWidget(self.seconds_radiobtn)

        # Time zone selection
        self.timezone_combo = ComboBox(self)
        self.timezone_combo.addItems(pytz.all_timezones)
        # Set default value to 'Asia/Shanghai'
        default_timezone = 'Asia/Shanghai'
        if default_timezone in pytz.all_timezones:
            index = self.timezone_combo.findText(default_timezone)
            if index != -1:
                self.timezone_combo.setCurrentIndex(index)

        # DateTime to Timestamp conversion
        datetime_layout = QHBoxLayout()
        self.datetime_edit = LineEdit(self)
        self.datetime_edit.textChanged.connect(self.convert_to_timestamp)
        self.datetime_edit.setPlaceholderText('输入时间 (YYYY-MM-DD HH:MM:SS)')
        
        # Initialize with current time in the default time zone
        tz = pytz.timezone(self.timezone_combo.currentText())
        current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        self.datetime_edit.setText(current_time)

        datetime_layout.addWidget(self.datetime_edit)
        datetime_layout.addWidget(QLabel('选择时区:'))
        datetime_layout.addWidget(self.timezone_combo)

        layout.addLayout(stamplayout)
        layout.addSpacing(10)
        layout.addLayout(datetime_layout)

        self.setLayout(layout)

    def convert_to_time(self):
        try:
            timestamp = int(self.timestamp_input.text())
            # Check if it's a millisecond timestamp
            if len(str(timestamp)) > 10:
                timestamp = timestamp / 1000.0
            tz = pytz.timezone(self.timezone_combo.currentText())
            dt = datetime.fromtimestamp(timestamp, tz)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            self.datetime_edit.textChanged.disconnect(self.convert_to_timestamp)
            self.datetime_edit.setText(formatted_time)
            self.datetime_edit.textChanged.connect(self.convert_to_timestamp)
        except ValueError:
            pass

    def convert_to_timestamp(self):
        try:
            dt_str = self.datetime_edit.text()
            tz = pytz.timezone(self.timezone_combo.currentText())
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            dt = tz.localize(dt)
            timestamp = dt.timestamp()

            if self.millisecs_radiobtn.isChecked():
                timestamp = int(timestamp * 1000)
            else:
                timestamp = int(timestamp)
            
            self.timestamp_input.textChanged.disconnect(self.convert_to_time)
            self.timestamp_input.setText(f'{timestamp}')
            self.timestamp_input.textChanged.connect(self.convert_to_time)
        except ValueError:
            pass


class OtherTool(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)    

        self.form_layout = QFormLayout(self)
        self.form_layout.setContentsMargins(0, 0, 0, 0)  # 设置布局的四个边距为0

        self.dalabel = QLabel(self.tr("测量点转换"))
        self.datools = DaTools()

        self.timelabel = QLabel(self.tr("时间转换"))
        self.timecovert = TimestampConverter()
        
        self.form_layout.addRow(self.dalabel, self.datools)
        self.form_layout.addRow(self.timelabel, self.timecovert)

class task_data_body_view(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('task_data_body_view')
        self.itemlayout = QVBoxLayout(self)
        self.itemlayout.setContentsMargins(0, 0, 0, 0)  # 设置布局的四个边距为0

        self.contentInput = PlainTextEdit()
        self.contentInput.setPlaceholderText(self.tr("请输入内容"))
        self.contentInput.textChanged.connect(self.onTextChanged)

        self.tree_widget = CustomTreeWidget()

        self.itemlayout.addWidget(self.contentInput)
        self.itemlayout.addSpacing(5)
        self.itemlayout.addWidget(self.tree_widget, 8)

    def onTextChanged(self):
        format_str = ''
        self.tree_widget.clear()
        self.tree_widget.last_item = None
        try:
            text = self.contentInput.toPlainText()
            result = []
            item_position = {}
            format_str = frame_fun.get_format_str(text)
            if text != '':
                frame = frame_fun.get_frame_list_from_str(text)
                custom_frame.task_data_frame(frame, 1, 0, result, 0)
                self.tree_widget.create_tree(None, result, item_position)
                self.tree_widget.expandAll()
                self.set_content_text(format_str)
            else:
                self.set_content_text(format_str)

        except Exception as e:
            print(e)
            if format_str != '':
                self.set_content_text(format_str)

    def set_content_text(self, format_str:str):
        self.contentInput.textChanged.disconnect(self.onTextChanged)
        self.contentInput.setPlainText(format_str)
        self.contentInput.textChanged.connect(self.onTextChanged)

class FrameInterface(QWidget):
    """ Pivot interface """

    Nav = Pivot

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.pivot = self.Nav(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.itemterface = CustomItem()
        self.tools = OtherTool()
        

        self.addSubInterface(self.itemterface, 'itemterface', self.tr('数据解析'))
        self.addSubInterface(self.tools, 'tools', self.tr('工具集合'))

        if versionctrl.is_release() == False:
            self.frame_tools = task_data_body_view()
            self.addSubInterface(self.frame_tools, 'frame_tools', self.tr('自定义报文解析'))

        self.vBoxLayout.addWidget(self.pivot, 1)
        self.vBoxLayout.addWidget(self.stackedWidget, 9)
        StyleSheet.NAVIGATION_VIEW_INTERFACE.apply(self)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.itemterface)
        self.pivot.setCurrentItem(self.itemterface.objectName())

        qrouter.setDefaultRouteKey(self.stackedWidget, self.itemterface.objectName())


    def addSubInterface(self, widget: QWidget, objectName, text):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())
        qrouter.push(self.stackedWidget, widget.objectName())

class CustomDataBaseInterface(FrameInterface):

    Nav = SegmentedWidget

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout.removeWidget(self.pivot)
        self.vBoxLayout.insertWidget(0, self.pivot)

class DataBaseInterface(GalleryInterface):
    """ Icon interface """

    def __init__(self, parent=None):
        t = Translator()
        super().__init__(
            title=t.icons,
            subtitle="数据库数据",
            parent=parent
        )
        self.setObjectName('CustomDataBaseInterface')
        self.qhlayout = QHBoxLayout(self)
        self.customframe = CustomDataBaseInterface()
        self.qhlayout.addWidget(self.customframe)
