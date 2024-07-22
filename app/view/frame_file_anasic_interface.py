from ..common.problam_analysic import ProblemAnalysic
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from .gallery_interface import GalleryInterface
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout,QFileDialog,QPushButton,QWidget,QLabel,QFormLayout,QApplication
from qfluentwidgets import FluentIconBase,PushButton,ToolButton,InfoBar,InfoBarPosition,ExpandSettingCard,ScrollArea,InfoBarIcon
from ..common.icon import Icon
from ..common.config import cfg
from ..common.problam_analysic import FileChooserWidget
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtCore import Qt,QCoreApplication,pyqtSignal,QObject
from PyQt5.QtGui import QIcon
from .analysic_interface import CustomTreeWidget
import threading
import queue
from ..plugins.frame_csg import FrameCsg
from ..plugins.MeterTask import MeterTask
from ..plugins.frame_cco import FrameCCO
from ..plugins.frame_fun import FrameFun as frame_fun
from ..plugins import protocol
from ..plugins.frame_analysic import FrameProcessor
from ..common.signal_bus import signalBus
from typing import Union


class DisplayResult(ExpandSettingCard):
    def __init__(self, icon: Union[str, QIcon, FluentIconBase], data, parent=None):
        super().__init__(icon, "解析结果", None, parent)
        self.setExpand(False)
        self.isExpand = False
        # self.card.removeEventFilter(self.card)
        # super().scrollLayout.removeWidget(super().view)
        # super().view.setParent(None)
        self.data = data
        self.card.expandButton.clicked.connect(self.value_change_handel)
        self.expandAni.valueChanged.connect(self.ExpandValueChanged)
        self.expandAni.valueChanged.disconnect(self._onExpandValueChanged)
        self.card.expandButton.clicked.disconnect(self.toggleExpand)

        self.set_data(self.data)

    def set_data(self, result):
        try:
            frame = result["报文"]
            frame_result = result["结果"]
            self.card.setTitle(frame)
            self.view = CustomTreeWidget(self.scrollWidget)
            item_position = {}
            result_list = []
            frame_fun.add_data(result_list, "帧域", "数据", "说明", [0,0], frame_result)
            print(result_list)
            self.view.create_tree(None, result_list, item_position)
            self.view.setHeaderHidden(True)
            self.view.collapseAll()
            self.view.setFixedHeight(50)
            self.scrollLayout.addWidget(self.view)
            self.view.expanded.connect(lambda: self.update_size(self.view))
            self._adjustViewSize() 
        except Exception as e:
            print(e)

    def ExpandValueChanged(self):
        self._onExpandValueChanged()
    
    def value_change_handel(self):
        if self.isExpand:
            self.view.collapseAll()
        else:
            self.view.expandAll()
        
        self.toggleExpand()
    
    def toggleExpand(self):
        """ toggle expand status """
        self.setExpand(not self.isExpand)

    def setExpand(self, isExpand: bool):
        """ set the expand status of card """
        if self.isExpand == isExpand:
            return

        # update style sheet
        self.isExpand = isExpand
        self.setProperty('isExpand', isExpand)
        self.setStyle(QApplication.style())

        # start expand animation
        if isExpand:
            h = self.view.sizeHint().height()
            self.verticalScrollBar().setValue(200)
            self.expandAni.setStartValue(h)
            self.expandAni.setEndValue(0)
        else:
            self.expandAni.setStartValue(0)
            self.expandAni.setEndValue(self.verticalScrollBar().maximum())

        self.expandAni.start()
        self.card.expandButton.setExpand(isExpand)

    def update_size(self, view:CustomTreeWidget):
        if view.is_expand():
            print("view expand")
            view.setFixedHeight(200)
        else:
            print("view noexpand")
            view.setFixedHeight(50)
        
        self.viewLayout.update()
        QCoreApplication.processEvents()
        self._adjustViewSize()
        
        
    
class FrameFileInterface(GalleryInterface):
    """ Icon interface """

    def __init__(self, parent=None):
        t = Translator()
        super().__init__(
            title=t.icons,
            subtitle="文件解析",
            parent=parent
        )
        self.setObjectName('FrameFileInterface')
        self.analisicthread = FrameProcessor()
        self.analisicthread.analisic_finish.connect(self.add_reult)
        # self.analisicthread.start()
        # signalBus.sendmessage.connect(self.add_frame)
        # signalBus.messagereceive.connect(self.add_frame) 

    def add_frame(self, object, frame):
        print("add frame",frame)
        frame = frame_fun.bytes_to_decimal_list(frame)
        self.analisicthread.add_frame(frame)

    def add_reult(self, result):
        try:
            analysiz_card = DisplayResult(
                FIF.EDUCATION,
                result,
                parent=self
            )
            self.vBoxLayout.addWidget(analysiz_card)
            return True
        except Exception as e:
            # infoBar = InfoBar(
            #     icon=InfoBarIcon.ERROR,
            #     title=self.tr('错误'),
            #     content=f"配置文件{conf_path}解析失败",
            #     orient=Qt.Vertical,
            #     isClosable=True,
            #     duration=2000,
            #     position=InfoBarPosition.TOP_RIGHT,
            #     parent=self
            # )
            # infoBar.show()
            return False