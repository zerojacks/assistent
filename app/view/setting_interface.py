# coding:utf-8
from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, Theme, CustomColorSettingCard,
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme,Pivot,qrouter,IndicatorPosition,FluentIconBase,
                            qconfig,LineEdit,ComboBox,PrimaryPushButton,SwitchButton,ConfigItem, SettingCard,PlainTextEdit,IconWidget,InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar,ProgressBar, FluentWindow, MessageBox
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths,QRegExp,QMetaObject
from PyQt5.QtGui import QDesktopServices,QIcon,QPainter,QColor,QRegExpValidator,QFont, QResizeEvent
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog,QPushButton,QFormLayout
from typing import Union
from ..common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11,REPO_OWNER,REPO_NAME
from ..common.signal_bus import signalBus
from ..common.style_sheet import StyleSheet
from ..plugins.update import UpdateThread
from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QSizePolicy
import serial.tools.list_ports
from ..plugins.signalCommunication import SerialPortThread,TcpServer,TcpClient,MQTTClientThread,BLEWorker
from ..common.commodule import CommType,commmbus
from ..components.state_tools import CustomStateToolTip
from ..common.icon import Icon
import serial,os,gc,asyncio
from PyQt5.QtNetwork import QAbstractSocket
from PyQt5.QtSerialPort import QSerialPort

class CustomVBoxLayout(QVBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 默认对齐方式为左对齐
        self.setAlignment(Qt.AlignLeft)

    def setAlignment(self, alignment):
        self.alignment = alignment

    def addItem(self, item):
        super().addItem(item)
        item.setAlignment(self.alignment)

class Tcpconfig(QWidget):
    def __init__(self, type, label1, label2, parent=None):
        super().__init__(parent=parent)
        self.type = type
        self.Thread = None
        self.stateTooltip = None
        self.tcp_server = None
        self.setFixedSize(300, 150)
        ip_validator = QRegExpValidator(QRegExp(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"))
        self.iplayout = QHBoxLayout()  # 使用水平布局
        self.iplabel = QLabel(label1)
        self.iplabel.setFont(QFont("Courier New", 12))
        self.iplabel.setAlignment(Qt.AlignLeft)
        self.ipNumberInput = LineEdit()
        self.ipNumberInput.setAlignment(Qt.AlignRight)
        self.ipNumberInput.setMaximumWidth(200)
        self.ipNumberInput.setValidator(ip_validator)
        self.iplayout.addWidget(self.iplabel, 1)
        self.iplayout.addWidget(self.ipNumberInput)

        self.portlayout = QHBoxLayout()  # 使用水平布局
        self.portlabel = QLabel()
        self.portlabel.setText(label2)
        self.portlabel.setFont(QFont("Courier New", 12))
        self.portlabel.setAlignment(Qt.AlignLeft)
        self.portNumberInput = LineEdit()
        self.portNumberInput.setMaximumWidth(200)
        self.portNumberInput.setAlignment(Qt.AlignRight)
        self.portlayout.addWidget(self.portlabel, 1)
        self.portlayout.addWidget(self.portNumberInput)

        self.qvlayout = CustomVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.iplayout)
        self.qvlayout.addLayout(self.portlayout)
        self.qvlayout.addSpacing(5)
        self.connectButon = PrimaryPushButton('连接')
        self.connectButon.setFixedWidth(95)
        self.qvlayout.setContentsMargins(0,0,0,0)
        self.qvlayout.addWidget(self.connectButon)
        self.init_widget()

    def init_widget(self):
        if self.type == CommType.TCP_CLIENT:
            ip = cfg.get(cfg.tcpClientIP)
            port = cfg.get(cfg.tcpClientPort)
        else:
            ip = cfg.get(cfg.tcpServerIP)
            port = cfg.get(cfg.tcpServerPort)
        self.ipNumberInput.setText(ip)
        self.portNumberInput.setText(str(port))
        self.connectButon.setCheckable(True)
        self.connectButon.setProperty('is_reconnectable', True)
        self.connectButon.clicked.connect(self.connectProcess)

    def setAlignment(self, a0: Union[Qt.Alignment, Qt.AlignmentFlag]):
        self.qvlayout.setAlignment(a0)

    def get_tcp_connect_param(self):
        port = self.portNumberInput.text()
        ipaddr = self.ipNumberInput.text()    
        return ipaddr,int(port)
    
    def set_edit_enable(self, enable=True):
        self.ipNumberInput.setEnabled(enable)
        self.portNumberInput.setEnabled(enable)
    
    def connectProcess(self):
        self.config_save()
        self.set_edit_enable(False)
        self.connectButon.setEnabled(False)
        is_reconnectable = self.connectButon.property('is_reconnectable')
        if is_reconnectable:
            # 按钮按下，尝试连接
            params = self.get_tcp_connect_param()
            if '' not in params:
                ipaddr, port = params
                # if self.tcp_server is not None:
                #     self.tcp_server.stopsingal.emit()
                #     self.tcp_server.deleteLater()
                #     self.tcp_server = None
                #     gc.collect()
                self.link_err_process(25)
                try:
                    if self.type == CommType.TCP_SERVICE:
                        self.tcp_server = TcpServer(ipaddr, port)
                        self.tcp_server.err_event.connect(self.link_err_process)
                        self.tcp_server.run()
                    elif self.type == CommType.TCP_CLIENT:
                        self.tcp_server = TcpClient(ipaddr, port)
                        self.tcp_server.err_event.connect(self.link_err_process)
                        # self.tcp_server.try_connect.emit()
                        self.tcp_server.start()
                except Exception as e:
                    print(f"creat error {e}")
        else:
            # 按钮未按下，断开连接
            if self.tcp_server is not None:
                if self.type == CommType.TCP_CLIENT:
                    signalBus.channel_disconnected.emit(self.type, self.tcp_server)
                else:
                    client_dic = self.tcp_server.get_socket_dic()
                    for worker in client_dic.values():
                        signalBus.channel_disconnected.emit(self.type, worker)
                
                self.tcp_server.stopsingal.emit()
                self.tcp_server.deleteLater()
                self.tcp_server = None
                gc.collect()
            
            self.set_edit_enable(True)
            
    def config_save(self):
        self.update_connect_param()
    def link_err_process(self, errcode):
        if errcode == 25:
            self.stateTooltip = CustomStateToolTip(FIF.SYNC, self.tr('正在连接...'), self.window())
            self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            self.stateTooltip.show()
        elif errcode == 255:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("连接成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('连接成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            
            self.connectButon.setProperty('is_reconnectable', False)
            self.connectButon.setText(self.tr('断开'))
        elif errcode == 404:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("断开成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('断开成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
        else:
            error_messages = {
                QAbstractSocket.SocketError.ConnectionRefusedError: '连接被远程主机拒绝',
                QAbstractSocket.SocketError.RemoteHostClosedError: '远程主机关闭了连接',
                QAbstractSocket.SocketError.HostNotFoundError: '未找到主机（主机名无效或无法解析）',
                QAbstractSocket.SocketError.SocketAccessError: '尝试访问套接字的操作被拒绝',
                QAbstractSocket.SocketError.SocketResourceError: '分配套接字资源失败',
                QAbstractSocket.SocketError.SocketTimeoutError: '操作在套接字上超时',
                QAbstractSocket.SocketError.DatagramTooLargeError: '尝试发送的数据报太大',
                QAbstractSocket.SocketError.NetworkError: '通用的网络错误，无法指定具体的错误',
                QAbstractSocket.SocketError.AddressInUseError: '地址已在使用中',
                QAbstractSocket.SocketError.SocketAddressNotAvailableError: '尝试绑定或连接到不可用的地址',
                QAbstractSocket.SocketError.UnsupportedSocketOperationError: '不支持的套接字操作',
                QAbstractSocket.SocketError.UnfinishedSocketOperationError: '套接字操作未完成',
                QAbstractSocket.SocketError.ProxyAuthenticationRequiredError: '代理要求身份验证',
                QAbstractSocket.SocketError.SslHandshakeFailedError: 'SSL 握手失败',
                QAbstractSocket.SocketError.ProxyConnectionRefusedError: '代理服务器拒绝连接',
                QAbstractSocket.SocketError.ProxyConnectionClosedError: '代理服务器关闭了连接',
                QAbstractSocket.SocketError.ProxyConnectionTimeoutError: '代理连接超时',
                QAbstractSocket.SocketError.ProxyNotFoundError: '代理服务器未找到',
                QAbstractSocket.SocketError.ProxyProtocolError: '代理协议错误',
                QAbstractSocket.SocketError.OperationError: '操作失败',
                QAbstractSocket.SocketError.SslInternalError: 'SSL 内部错误',
                QAbstractSocket.SocketError.SslInvalidUserDataError: 'SSL 无效用户数据错误',
                QAbstractSocket.SocketError.TemporaryError: '暂时性错误，可以尝试再次执行操作',
                QAbstractSocket.SocketError.UnknownSocketError: '未知的套接字错误，无法指定具体的错误',
                # 添加其他可能的错误代码和对应的描述信息
            }
            error_message = error_messages.get(errcode, f'Socket Error: {errcode} 😞')
            if self.stateTooltip is None:
                self.stateTooltip = CustomStateToolTip(Icon.ERROR, self.tr(error_message), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
            else:
                self.stateTooltip.seticon(Icon.ERROR)
                self.stateTooltip.setTitle(error_message)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            
            self.stateTooltip.setState(True)
            self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
            self.stateTooltip = None

        if errcode != 25:
            self.connectButon.setEnabled(True)
        if errcode not in (25, 255):
            self.set_edit_enable(True)
    def update_connect_param(self):
        # 设置串口配置
        if self.type == CommType.TCP_CLIENT:
            params = self.get_tcp_connect_param()
            ip, port = params
            cfg.set(cfg.tcpClientIP, ip)
            cfg.set(cfg.tcpClientPort, port)
        else:
            params = self.get_tcp_connect_param()
            ip, port = params
            cfg.set(cfg.tcpServerIP, ip)
            cfg.set(cfg.tcpServerPort, port)
    def get_connect_result(self, status):
        self.connectStatus = status
        self.onStateButtonClicked()
        commmbus.link_port = self.commnectModule
        if self.connecttype == CommType.SERIAL:
            commmbus.channel = self.commnectModule.serial
        elif self.connecttype == CommType.TCP_CLIENT:
            commmbus.channel = self.commnectModule.tcp_socket
        elif self.connecttype == CommType.TCP_SERVICE:
            commmbus.channel = self.commnectModule.clientSocket
        commmbus.link_status = status
        if status:
            self.Conconfig.set_edit_enable(self.connecttype, False)
            self.connectButon.setEnabled(True)
        else:
            self.connectButon.setEnabled(True)
            self.Conconfig.set_edit_enable(self.connecttype, True)

    def tcp_socket_change_process(self,socket_list):
        commmbus.tcpSocket = socket_list
        signalBus.tcpSocketChange.emit(socket_list)
        
    
class SerialConfig(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.serial_manager = None
        self.stateTooltip = None
        self.setFixedSize(300, 250)
        self.serialPortlayout = QHBoxLayout()  # 使用水平布局
        self.serialPortlabel = QLabel('串口号')
        self.serialPortlabel.setAlignment(Qt.AlignLeft)

        self.serialcomboBox = ComboBox()
        self.serialPortlayout.addWidget(self.serialPortlabel)
        self.serialPortlayout.addWidget(self.serialcomboBox)

        self.Budratelayout = QHBoxLayout()  # 使用水平布局
        self.Budratelabel = QLabel('波特率')
        self.Budratelabel.setAlignment(Qt.AlignLeft)
        self.BudrateComBox = ComboBox()
        self.Budratelayout.addWidget(self.Budratelabel)
        self.Budratelayout.addWidget(self.BudrateComBox)

        self.Checklayout = QHBoxLayout()  # 使用水平布局
        self.Checklabel = QLabel('校验位')
        self.Checklabel.setAlignment(Qt.AlignLeft)
        self.CheckComBox = ComboBox()
        self.Checklayout.addWidget(self.Checklabel)
        self.Checklayout.addWidget(self.CheckComBox)

        self.DataBitlayout = QHBoxLayout()  # 使用水平布局
        self.DataBitlabel = QLabel('数据位')
        self.DataBitlabel.setAlignment(Qt.AlignLeft)
        self.DataBitComBox = ComboBox()
        self.DataBitlayout.addWidget(self.DataBitlabel)
        self.DataBitlayout.addWidget(self.DataBitComBox)

        self.StopBitlayout = QHBoxLayout()  # 使用水平布局
        self.StopBitlabel = QLabel('停止位')
        self.StopBitlabel.setAlignment(Qt.AlignLeft)
        self.StopBitComBox = ComboBox()
        self.StopBitlayout.addWidget(self.StopBitlabel)
        self.StopBitlayout.addWidget(self.StopBitComBox)

        self.connectButon = PrimaryPushButton('连接')
        self.connectButon.setFixedWidth(85)

        self.qvlayout = CustomVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.serialPortlayout)
        self.qvlayout.addLayout(self.Budratelayout)
        self.qvlayout.addLayout(self.Checklayout)
        self.qvlayout.addLayout(self.DataBitlayout)
        self.qvlayout.addLayout(self.StopBitlayout)
        self.qvlayout.addSpacing(5)
        self.qvlayout.addWidget(self.connectButon)
        self.qvlayout.setContentsMargins(0,0,0,0)

        self._init_Widgets()

    def _init_Widgets(self):
        self.populate_serial_ports()
        self.Budrate = ['2400', '4800', '9600', '115200']
        self.BudrateComBox.addItems(self.Budrate)
        self.check = ['奇校验','偶校验','无校验']
        self.CheckComBox.addItems(self.check)
        self.databit=['5','6', '7','8']
        self.DataBitComBox.addItems(self.databit)
        self.stopbit = ['1','1.5','2']
        self.StopBitComBox.addItems(self.stopbit)
        self.connectButon.setProperty('is_reconnectable', True)
        # 读取串口配置
        baud_rate = cfg.get(cfg.serial_BaudRate)
        parity = cfg.get(cfg.serial_parity)
        data_bits = cfg.get(cfg.serial_databit)
        stop_bits = cfg.get(cfg.serial_stopbit)
        if baud_rate:
            self.BudrateComBox.setCurrentText(f'{baud_rate}')
        else:
            self.BudrateComBox.setCurrentIndex(2)
        
        if parity:
            self.CheckComBox.setCurrentText(parity)
        else:
            self.CheckComBox.setCurrentText(1)

        if data_bits:
            self.DataBitComBox.setCurrentText(f"{data_bits}")
        else:
            self.DataBitComBox.setCurrentIndex(3)
        
        if stop_bits:
            self.StopBitComBox.setCurrentText(f"{stop_bits}")
        else:
            self.StopBitComBox.setCurrentIndex(3)

        self.qvlayout.setContentsMargins(0,0,0,0)
        self.qvlayout.setSpacing(2)
        self.connectButon.clicked.connect(self.connect_serial)

    def setAlignment(self, a0: Union[Qt.Alignment, Qt.AlignmentFlag]):
        self.qvlayout.setAlignment(a0)

    def populate_serial_ports(self):
        serial_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serialcomboBox.addItems(serial_ports)

    def get_serial_connect_param(self):
        comname = self.serialcomboBox.currentText()
        budrate =  int(self.Budrate[self.BudrateComBox.currentIndex()])
        check = self.get_serial_check()
        databit = self.get_serial_datait()
        stopbit = self.get_serial_stopbit()
        return comname,budrate,check,databit,stopbit
    
    def get_serial_check(self):
        if self.CheckComBox.currentIndex() == 0:
            check = QSerialPort.Parity.OddParity
        elif self.CheckComBox.currentIndex() == 1:
            check = QSerialPort.Parity.EvenParity
        elif self.CheckComBox.currentIndex() == 2:
            check = QSerialPort.Parity.NoParity
        else:
            check = QSerialPort.Parity.NoParity
        return check
    
    def get_serial_datait(self):
        if self.DataBitComBox.currentIndex() == 0:
            databit = QSerialPort.DataBits.Data5
        elif self.DataBitComBox.currentIndex() == 1:
            databit = QSerialPort.DataBits.Data6
        elif self.DataBitComBox.currentIndex == 2:
            databit = QSerialPort.DataBits.Data7
        elif self.DataBitComBox.currentIndex() == 3:
            databit = QSerialPort.DataBits.Data8
        else:
            databit = QSerialPort.DataBits.Data8
        return databit
    
    def get_serial_stopbit(self):
        if self.StopBitComBox.currentIndex() == 0:
            stopbit = QSerialPort.StopBits.OneStop
        elif self.StopBitComBox.currentIndex() == 1:
            stopbit = QSerialPort.StopBits.OneAndHalfStop
        elif self.StopBitComBox.currentIndex() == 2:
            stopbit = QSerialPort.StopBits.TwoStop
        else:
            stopbit = QSerialPort.StopBits.OneStop
        return stopbit
    
    def set_edit_enable(self, enable=True):
        self.serialcomboBox.setEnabled(enable)
        self.BudrateComBox.setEnabled(enable)
        self.CheckComBox.setEnabled(enable)
        self.DataBitComBox.setEnabled(enable)
        self.StopBitComBox.setEnabled(enable)
    def update_connect_param(self):
        # 设置串口配置
        comname,budrate,check,databit,stopbit = self.get_serial_connect_param()
        cfg.set(cfg.serial_BaudRate, budrate)
        cfg.set(cfg.serial_parity, check)
        cfg.set(cfg.serial_databit, databit)
        cfg.set(cfg.serial_stopbit, stopbit)
    def connect_serial(self):
        self.set_edit_enable(False)
        self.connectButon.setEnabled(False)
        self.update_connect_param()
        is_reconnectable = self.connectButon.property('is_reconnectable')
        if is_reconnectable:
            self.link_err_process(25)
            try:
                comname,budrate,check,databit,stopbit = self.get_serial_connect_param()
                self.serial_manager = SerialPortThread(comname,budrate,check,databit,stopbit)
                self.serial_manager.err_event.connect(self.link_err_process)
                self.serial_manager.start()
            except Exception as e:
                pass
        else:
            self.set_edit_enable(True)
            self.serial_manager.stopsingal.emit()
            signalBus.channel_disconnected.emit(CommType.SERIAL, self.serial_manager)
    def link_err_process(self, errcode):
        if errcode == 25:
            self.stateTooltip = CustomStateToolTip(FIF.SYNC, self.tr('正在连接...'), self.window())
            self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            self.stateTooltip.show()
        elif errcode == 255:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("连接成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('连接成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            
            self.connectButon.setProperty('is_reconnectable', False)
            self.connectButon.setText(self.tr('断开'))
        elif errcode == 404:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("断开成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('断开成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
        else:
            error_messages = {
                QSerialPort.SerialPortError.NoError: '串口操作成功',
                QSerialPort.SerialPortError.DeviceNotFoundError: '未找到指定的串口设备',
                QSerialPort.SerialPortError.PermissionError: '没有权限访问串口设备',
                QSerialPort.SerialPortError.OpenError: '打开串口设备时发生错误',
                QSerialPort.SerialPortError.ParityError: '串口通信中的奇偶校验错误',
                QSerialPort.SerialPortError.FramingError: '帧错误，即接收到的数据无法解析成有效的帧',
                QSerialPort.SerialPortError.BreakConditionError: '接收到了中断信号',
                QSerialPort.SerialPortError.WriteError: '写入串口设备时发生错误',
                QSerialPort.SerialPortError.ReadError: '读取串口设备时发生错误',
                QSerialPort.SerialPortError.ResourceError: '资源错误',
                QSerialPort.SerialPortError.UnsupportedOperationError: '不支持的操作错误',
                QSerialPort.SerialPortError.TimeoutError: '串口操作超时',
                QSerialPort.SerialPortError.NotOpenError: '串口没有打开',
                QSerialPort.SerialPortError.UnknownError: '未知错误',
                # 添加其他可能的错误代码和对应的描述信息
            }
            error_message = error_messages.get(errcode, f'Socket Error: {errcode} 😞')
            if self.stateTooltip is None:
                self.stateTooltip = CustomStateToolTip(Icon.ERROR, self.tr(error_message), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
            else:
                self.stateTooltip.seticon(Icon.ERROR)
                self.stateTooltip.setTitle(error_message)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            
            self.stateTooltip.setState(True)
            self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
            self.stateTooltip = None

        if errcode != 25:
            self.connectButon.setEnabled(True)  
        if errcode not in (25, 255):
            self.set_edit_enable(True) 

class MqttConfig(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.type = CommType.MQTT
        self.stateTooltip = None
        self.mqtt_thread = None
        self.setFixedSize(300, 250)
        ip_validator = QRegExpValidator(QRegExp(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"))
        self.iplayout = QHBoxLayout()  # 使用水平布局
        self.iplabel = QLabel("远程地址")
        self.iplabel.setFont(QFont("Courier New", 12))
        self.iplabel.setAlignment(Qt.AlignLeft)
        self.ipNumberInput = LineEdit()
        self.ipNumberInput.setAlignment(Qt.AlignRight)
        self.ipNumberInput.setMaximumWidth(200)
        self.ipNumberInput.setValidator(ip_validator)
        self.iplayout.addWidget(self.iplabel, 1)
        self.iplayout.addWidget(self.ipNumberInput)

        self.portlayout = QHBoxLayout()  # 使用水平布局
        self.portlabel = QLabel()
        self.portlabel.setText("端口")
        self.portlabel.setFont(QFont("Courier New", 12))
        self.portlabel.setAlignment(Qt.AlignLeft)
        self.portNumberInput = LineEdit()
        self.portNumberInput.setMaximumWidth(200)
        self.portNumberInput.setAlignment(Qt.AlignRight)
        self.portlayout.addWidget(self.portlabel, 1)
        self.portlayout.addWidget(self.portNumberInput)

        self.usernamelayout = QHBoxLayout()  # 使用水平布局
        self.usernamelabel = QLabel()
        self.usernamelabel.setText("用户名")
        self.usernamelabel.setFont(QFont("Courier New", 12))
        self.usernamelabel.setAlignment(Qt.AlignLeft)
        self.usernameNumberInput = LineEdit()
        self.usernameNumberInput.setMaximumWidth(200)
        self.usernameNumberInput.setAlignment(Qt.AlignRight)
        self.usernamelayout.addWidget(self.usernamelabel, 1)
        self.usernamelayout.addWidget(self.usernameNumberInput)

        self.passwdlayout = QHBoxLayout()  # 使用水平布局
        self.passwdlabel = QLabel()
        self.passwdlabel.setText("密码")
        self.passwdlabel.setFont(QFont("Courier New", 12))
        self.passwdlabel.setAlignment(Qt.AlignLeft)
        self.passwdNumberInput = LineEdit()
        self.passwdNumberInput.setMaximumWidth(200)
        self.passwdNumberInput.setAlignment(Qt.AlignRight)
        self.passwdlayout.addWidget(self.passwdlabel, 1)
        self.passwdlayout.addWidget(self.passwdNumberInput)

        self.qvlayout = CustomVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.iplayout)
        self.qvlayout.addLayout(self.portlayout)
        self.qvlayout.addLayout(self.usernamelayout)
        self.qvlayout.addLayout(self.passwdlayout)
        self.qvlayout.addSpacing(5)
        self.connectButon = PrimaryPushButton('连接')
        self.connectButon.setFixedWidth(95)
        self.qvlayout.setContentsMargins(0,0,0,0)
        self.qvlayout.addWidget(self.connectButon)
        self.init_widget()

    def init_widget(self):
        ip = cfg.get(cfg.mqttip)
        port = cfg.get(cfg.mqttport)
        user = cfg.get(cfg.mqttuser)
        passwd = cfg.get(cfg.mqttpasswd)
        self.ipNumberInput.setText(ip)
        self.portNumberInput.setText(str(port))
        self.usernameNumberInput.setText(str(user))
        self.passwdNumberInput.setText(str(passwd))
        self.connectButon.setCheckable(True)
        self.connectButon.setProperty('is_reconnectable', True)
        self.connectButon.clicked.connect(self.connect_mqtt)

    def setAlignment(self, a0: Union[Qt.Alignment, Qt.AlignmentFlag]):
        self.qvlayout.setAlignment(a0)

    def get_connect_param(self):
        port = self.portNumberInput.text()
        ipaddr = self.ipNumberInput.text()   
        name = self.usernameNumberInput.text()
        passwd = self.passwdNumberInput.text() 
        return ipaddr,int(port), name, passwd
    
    def set_edit_enable(self, enable=True):
        self.ipNumberInput.setEnabled(enable)
        self.portNumberInput.setEnabled(enable)
        self.usernameNumberInput.setEnabled(enable)
        self.passwdNumberInput.setEnabled(enable)

    def update_connect_param(self):
        # 设置串口配置
        ip, port, name, passwd = self.get_connect_param()
        cfg.set(cfg.mqttip, ip)
        cfg.set(cfg.mqttport, port)
        cfg.set(cfg.mqttuser, name)
        cfg.set(cfg.mqttpasswd, passwd)
    def connect_mqtt(self):
        self.set_edit_enable(False)
        self.connectButon.setEnabled(False)
        self.update_connect_param()
        is_reconnectable = self.connectButon.property('is_reconnectable')
        if is_reconnectable:
            self.link_err_process(25)
            try:
                ip, port, name, passwd = self.get_connect_param()
                self.mqtt_thread = MQTTClientThread(ip, port, name, passwd)
                self.mqtt_thread.err_event.connect(self.link_err_process)
                self.mqtt_thread.start()
            except Exception as e:
                pass
        else:
            self.set_edit_enable(True)
            self.mqtt_thread.stopsingal.emit()
            signalBus.channel_disconnected.emit(CommType.MQTT, self.mqtt_thread)
    def link_err_process(self, errcode):
        if errcode == 25:
            self.stateTooltip = CustomStateToolTip(FIF.SYNC, self.tr('正在连接...'), self.window())
            self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            self.stateTooltip.show()
        elif errcode == 255:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("连接成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('连接成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            
            self.connectButon.setProperty('is_reconnectable', False)
            self.connectButon.setText(self.tr('断开'))
        elif errcode == 404:
            if self.stateTooltip:
                self.stateTooltip.setTitle(self.tr("断开成功"))
                self.stateTooltip.seticon(FIF.COMPLETED)
                self.stateTooltip.setState(True)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip = None
            else:
                self.stateTooltip = CustomStateToolTip(FIF.COMPLETED, self.tr('断开成功'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
                self.stateTooltip.setState(True)
                self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
        else:
            error_messages = {
                QSerialPort.SerialPortError.NoError: '串口操作成功',
                QSerialPort.SerialPortError.DeviceNotFoundError: '未找到指定的串口设备',
                QSerialPort.SerialPortError.PermissionError: '没有权限访问串口设备',
                QSerialPort.SerialPortError.OpenError: '打开串口设备时发生错误',
                QSerialPort.SerialPortError.ParityError: '串口通信中的奇偶校验错误',
                QSerialPort.SerialPortError.FramingError: '帧错误，即接收到的数据无法解析成有效的帧',
                QSerialPort.SerialPortError.BreakConditionError: '接收到了中断信号',
                QSerialPort.SerialPortError.WriteError: '写入串口设备时发生错误',
                QSerialPort.SerialPortError.ReadError: '读取串口设备时发生错误',
                QSerialPort.SerialPortError.ResourceError: '资源错误',
                QSerialPort.SerialPortError.UnsupportedOperationError: '不支持的操作错误',
                QSerialPort.SerialPortError.TimeoutError: '串口操作超时',
                QSerialPort.SerialPortError.NotOpenError: '串口没有打开',
                QSerialPort.SerialPortError.UnknownError: '未知错误',
                # 添加其他可能的错误代码和对应的描述信息
            }
            error_message = error_messages.get(errcode, 'MQTT 连接失败 😞')
            if self.stateTooltip is None:
                self.stateTooltip = CustomStateToolTip(Icon.ERROR, self.tr(error_message), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
            else:
                self.stateTooltip.seticon(Icon.ERROR)
                self.stateTooltip.setTitle(error_message)
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            
            self.stateTooltip.setState(True)
            self.stateTooltip = None
            self.connectButon.setProperty('is_reconnectable', True)
            self.connectButon.setText(self.tr('连接'))
            self.stateTooltip = None

        if errcode != 25:
            self.connectButon.setEnabled(True)  
        if errcode not in (25, 255):
            self.set_edit_enable(True) 

class BleConnectConfig(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.type = CommType.BLUETOOTH
        self.worker = None
        self.setFixedSize(300, 200)
        self.initUI()
    def initUI(self):
        self.devicelayout = QHBoxLayout()
        self.devicelabel = QLabel(self.tr("设备"))
        self.devicelabel.setAlignment(Qt.AlignLeft)
        self.devcombox = ComboBox()
        self.devcombox.setFixedWidth(250)
        self.devicelayout.addWidget(self.devicelabel, 1)
        self.devicelayout.addWidget(self.devcombox)

        self.servicelayout = QHBoxLayout()
        self.servicelabel = QLabel(self.tr("服务"))
        self.servicelabel.setAlignment(Qt.AlignLeft)
        self.servicecom = ComboBox()
        self.servicecom.setFixedWidth(250)
        self.servicelayout.addWidget(self.servicelabel, 1)
        self.servicelayout.addWidget(self.servicecom)


        self.chartlayout = QHBoxLayout()
        self.characteristicslabel = QLabel(self.tr("特征"))
        self.characteristicslabel.setAlignment(Qt.AlignLeft)
        self.characteristicscom = ComboBox()
        self.characteristicscom.setFixedWidth(250)
        self.chartlayout.addWidget(self.characteristicslabel, 1)
        self.chartlayout.addWidget(self.characteristicscom)

        self.btpayout = QHBoxLayout()
        self.scanbutton = PrimaryPushButton(self.tr("扫描"))
        self.connebutton = PrimaryPushButton(self.tr("连接"))
        self.uuidbutton = PrimaryPushButton(self.tr("设置特征"))
        self.btpayout.addWidget(self.scanbutton)
        self.btpayout.addWidget(self.connebutton)
        self.btpayout.addWidget(self.uuidbutton)

        self.qvlayout = CustomVBoxLayout(self)  # 使用垂直布局
        self.qvlayout.addLayout(self.devicelayout)
        self.qvlayout.addLayout(self.servicelayout)
        self.qvlayout.addLayout(self.chartlayout)
        self.qvlayout.addLayout(self.btpayout)
        self.qvlayout.addSpacing(5)
        self.qvlayout.setContentsMargins(0,0,0,0)

        self.scanbutton.setCheckable(True)
        self.scanbutton.setProperty('is_reconnectable', True)
        self.connebutton.setCheckable(True)
        self.connebutton.setProperty('is_reconnectable', True)
        self.scanbutton.setFixedWidth(95)
        self.connebutton.setFixedWidth(95)
        self.init_slot()

    def init_slot(self):
        self.scanbutton.clicked.connect(self.scan_devices)
        self.connebutton.clicked.connect(self.connect_device)
        self.uuidbutton.clicked.connect(self.set_characteristics)

    def init_blework(self):
        self.worker = BLEWorker()
        self.worker.devices_discovered.connect(self.display_devices)
        self.worker.services_discovered.connect(self.display_services)
        self.worker.connection_status.connect(self.handle_connection_status)
        self.worker.start()

    def setAlignment(self, a0: Union[Qt.Alignment, Qt.AlignmentFlag]):
        self.qvlayout.setAlignment(a0)

    def scan_devices(self):
        self.devcombox.clear()
        if self.worker is None:
            self.init_blework()

        self.set_edit_enable(False)
        self.scanbutton.setEnabled(False)
        is_reconnectable = self.scanbutton.property('is_reconnectable')
        if is_reconnectable:
            try:
                asyncio.run_coroutine_threadsafe(self.worker.scan_devices(), self.worker.loop)
                self.scanbutton.setProperty('is_reconnectable', False)
            except Exception as e:
                pass
        else:
            self.set_edit_enable(True)
            self.scanbutton.setProperty('is_reconnectable', True)

    def display_devices(self, devices):
        for device in devices:
            self.devcombox.addItem(f"{device.name} ({device.address})")
        self.set_edit_enable(True)
        self.scanbutton.setProperty('is_reconnectable', True)

    def connect_device(self):
        selected_item = self.devcombox.currentText()
        if len(selected_item) == 0:
            InfoBar.warning(
                title=self.tr('告警'),
                content=self.tr("未选择设备!"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        if self.worker is None:
            self.init_blework()

        self.set_edit_enable(False)
        self.connebutton.setEnabled(False)
        is_reconnectable = self.connebutton.property('is_reconnectable')
        if is_reconnectable:
            try:
                address = selected_item.split('(')[-1].strip(')')
                asyncio.run_coroutine_threadsafe(self.worker.connect_device(address), self.worker.loop)
            except Exception as e:
                print(e)
        else:
            try:
                self.connebutton.setProperty('is_reconnectable', True)
                asyncio.run_coroutine_threadsafe(self.worker.disconnect_device(), self.worker.loop)
            except Exception as e:
                print(e)
            self.set_edit_enable(True)


    def handle_connection_status(self, status):
        if status:
            print("连接成功")
            self.connebutton.setText(self.tr('断开'))
            self.connebutton.setEnabled(True)
            self.servicecom.setEnabled(True)
            self.characteristicscom.setEnabled(True)
            self.uuidbutton.setEnabled(True)
            self.connebutton.setProperty('is_reconnectable', False)
        else:
            print("连接失败")
            self.connebutton.setText(self.tr('连接'))
            self.set_edit_enable(True) 
            self.connebutton.setProperty('is_reconnectable', True)
    def set_characteristics(self):
        text = self.characteristicscom.currentText()
        if text != "":
            uuid = text.split(':')[0].strip()
            print("设置uuid", uuid)
            asyncio.run_coroutine_threadsafe(self.worker.set_characteristic_uuid(uuid), self.worker.loop)

    def display_services(self, services):
        self.servicecom.clear()
        self.characteristicscom.clear()
        for service in services:
            self.servicecom.addItem(f"{service['uuid']}: {service['description']}")
            for char in service['characteristics']:
                self.characteristicscom.addItem(f"{char['uuid']}: {char['description']}")

    def set_edit_enable(self, enable=True):
        self.devcombox.setEnabled(enable)
        self.servicecom.setEnabled(enable)
        self.characteristicscom.setEnabled(enable)
        self.scanbutton.setEnabled(enable)
        self.connebutton.setEnabled(enable)
        self.uuidbutton.setEnabled(enable)

class ConnectConfig(QWidget):
    """ Pivot interface """

    Nav = Pivot
    sizeChanged = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.connectType = CommType.TCP_CLIENT
        self.pivot = self.Nav(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.setFixedSize(800, 300)
        text = "<font>端&nbsp;&nbsp;&nbsp;口</font>"
        self.tcpclientInterface = Tcpconfig(CommType.TCP_CLIENT, '远程地址',text,self)
        self.tcpserverInterface = Tcpconfig(CommType.TCP_SERVICE, '本地地址',text, self)
        self.serialInterface = SerialConfig(self)
        self.mqttInterface = MqttConfig(self)
        self.bleconnectinterface = BleConnectConfig(self)
        # add items to pivot
        self.addSubInterface(self.tcpclientInterface, 'tcpclientInterface', self.tr('TCP客户端'))
        self.addSubInterface(self.tcpserverInterface, 'tcpserverInterface', self.tr('TCP服务器'))
        self.addSubInterface(self.serialInterface, 'serialInterface', self.tr('串口'))
        self.addSubInterface(self.mqttInterface, 'mqttInterface', self.tr('MQTT'))
        self.addSubInterface(self.bleconnectinterface, "bleconnectinterface", self.tr('蓝牙'))
        self.vBoxLayout.addWidget(self.pivot, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        StyleSheet.NAVIGATION_VIEW_INTERFACE.apply(self)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.onCurrentIndexChanged(0)
        self.stackedWidget.setCurrentWidget(self.tcpclientInterface)
        self.pivot.setCurrentItem(self.tcpclientInterface.objectName())

        qrouter.setDefaultRouteKey(self.stackedWidget, self.tcpclientInterface.objectName())

    def addSubInterface(self, widget: QWidget, objectName, text):
        widget.setObjectName(objectName)
        widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.setFixedSize(widget.width() + 40, widget.height() + 40)
        self.pivot.setCurrentItem(widget.objectName())
        qrouter.push(self.stackedWidget, widget.objectName())
        if index == 0:
            self.connectType = CommType.TCP_CLIENT
        elif index == 1:
            self.connectType = CommType.TCP_SERVICE
        elif index == 2:
            self.connectType = CommType.SERIAL
        elif index == 3:
            self.connectType = CommType.MQTT
        elif index == 4:
            self.connectType = CommType.BLUETOOTH

    def resizeEvent(self, event):
        # 大小变化事件处理
        new_size = event.size()
        # 在这里执行你想要的操作
        # 发射自定义信号以通知大小变化
        self.sizeChanged.emit()
        return super().resizeEvent(event)

    def get_connect_type(self)->CommType:
        return self.connectType
    
    def get_serial_connect_param(self):
        return self.serialInterface.get_serial_connect_param()
    
    def get_tcp_connect_param(self):
        if self.connectType == CommType.TCP_CLIENT:
            return self.tcpclientInterface.get_tcp_connect_param()
        elif self.connectType == CommType.TCP_SERVICE:
            return self.tcpserverInterface.get_tcp_connect_param()
    def set_edit_enable(self, type, enable=True):
        if self.connectType == CommType.TCP_CLIENT:
            self.tcpclientInterface.set_edit_enable(enable)
        elif self.connectType == CommType.TCP_SERVICE:
            self.tcpserverInterface.set_edit_enable(enable)    
        else:
            self.serialInterface.set_edit_enable(enable)
    
class ConnectCard(QFrame):
    """ Connnect card """

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, parent=None):
        super().__init__(parent=parent)
        self.stateTooltip = None
        self.connectStatus = False
        self.setObjectName('setting_card')
        self.hBoxLayout = QHBoxLayout(self)
        self.Conconfig = ConnectConfig()
        self.Conconfig.resizeEvent = self.resizeEvent
        self.hBoxLayout.addWidget(self.Conconfig,0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)
        StyleSheet.SET_CARD.apply(self)
        self.commnectModule = None
        self.connecttype = None
        self.update_size()
    
    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        self.update_size()
        return super().resizeEvent(a0)
    def update_size(self):
        self.setFixedHeight(self.Conconfig.height() + 15)
    
    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        if isDarkTheme():
            painter.setBrush(QColor(255, 255, 255, 13))
            painter.setPen(QColor(0, 0, 0, 50))
        else:
            painter.setBrush(QColor(255, 255, 255, 170))
            painter.setPen(QColor(0, 0, 0, 19))

        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

    def get_connect_result(self, status):
        self.connectStatus = status
        self.onStateButtonClicked()
        commmbus.connecttype = self.connecttype
        commmbus.link_port = self.commnectModule
        if self.connecttype == CommType.SERIAL:
            commmbus.channel = self.commnectModule.serial
        elif self.connecttype == CommType.TCP_CLIENT:
            commmbus.channel = self.commnectModule.tcp_socket
        elif self.connecttype == CommType.TCP_SERVICE:
            commmbus.channel = self.commnectModule.clientSocket
        commmbus.link_status = status
        if status:
            self.Conconfig.set_edit_enable(self.connecttype, False)
            self.connectButon.setEnabled(True)
        else:
            self.connectButon.setEnabled(True)
            self.Conconfig.set_edit_enable(self.connecttype, True)

    def tcp_socket_change_process(self,socket_list):
        commmbus.tcpSocket = socket_list
        signalBus.tcpSocketChange.emit(socket_list)
        
    def onStateButtonClicked(self):
        text = self.connectButon.text()
        if self.stateTooltip:
            if text == '连接':
                # self.stateTooltip.setTitle('连接结果')
                if self.connectStatus:
                    self.stateTooltip.seticon(FIF.COMPLETED)
                    self.stateTooltip.setTitle(
                        self.tr('连接成功') + ' 😆')
                    self.stateTooltip.setState(True)
                    self.connectButon.setText('断开')
                else:
                    self.stateTooltip.seticon(Icon.ERROR)
                    self.stateTooltip.setTitle(
                        self.tr('连接失败') + ' 😒')
                    self.stateTooltip.setState(True)
                    self.connectButon.setText('连接')
            else:
                # self.stateTooltip.setTitle('断开结果')
                if self.connectStatus:
                    self.stateTooltip.seticon(Icon.ERROR)
                    self.stateTooltip.setTitle(
                        self.tr('断开失败') + ' 😒')
                    self.stateTooltip.setState(True)
                    self.connectButon.setText('断开')
                else:
                    self.stateTooltip.seticon(FIF.COMPLETED)
                    self.stateTooltip.setTitle(
                        self.tr('已断开') + ' 😆')
                    self.stateTooltip.setState(True)
                    self.connectButon.setText('连接')

            self.stateTooltip = None
        else:
            if text == '连接':
                self.stateTooltip = CustomStateToolTip(
                    FIF.SYNC, self.tr('正在连接...'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()
            else:
                self.stateTooltip = CustomStateToolTip(
                    FIF.SYNC, self.tr('正在断开...'), self.window())
                self.stateTooltip.move(self.stateTooltip.getSuitablePos())
                self.stateTooltip.show()

    def update_connect_param(self, params):
        # 设置串口配置
        if self.connecttype == CommType.SERIAL:
            comname, budrate, check, data, stop = params
            cfg.set(cfg.serial_BaudRate, budrate)
            if check == serial.PARITY_ODD:
                check = "奇校验"
            elif check == serial.PARITY_EVEN:
                check = "偶校验"
            else:
                check = "无校验"
            cfg.set(cfg.serial_parity,check)
            cfg.set(cfg.serial_databit,data)
            cfg.set(cfg.serial_stopbit,stop)
        elif self.connecttype == CommType.TCP_CLIENT:
            ip, port = params
            cfg.set(cfg.tcpClientIP, ip)
            cfg.set(cfg.tcpClientPort, port)
        else:
            ip, port = params
            cfg.set(cfg.tcpServerIP, ip)
            cfg.set(cfg.tcpServerPort, port)


class MultireportCard(QWidget):
    checkedChanged = pyqtSignal(bool)
    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, ReportconfigItem: ConfigItem = None,
                 adressconfigItem: ConfigItem = None, parent=None):
        super().__init__(parent=parent)
        self.stateTooltip = None
        self.connectStatus = False
        self.reportconfig = ReportconfigItem
        self.adressConfig = adressconfigItem
        self.setObjectName('MultireportCard')

        self.switchButton = SwitchButton(
            self.tr('关'), self, IndicatorPosition.RIGHT)
        
        self.hBoxlayout = QHBoxLayout()
        self.PlainTextEdit = PlainTextEdit()
        self.button = PrimaryPushButton(self.tr('设置地址'))
        self.hBoxlayout.addWidget(self.PlainTextEdit, 0, Qt.AlignLeft)
        self.hBoxlayout.addSpacing(5)
        self.hBoxlayout.addWidget(self.button,0, Qt.AlignRight)
        self.PlainTextEdit.setFixedSize(200, 100)

        self.button.clicked.connect(self.__onTextChanged)
        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)
        if ReportconfigItem:
            self.setValue(qconfig.get(ReportconfigItem))
            ReportconfigItem.valueChanged.connect(self.setValue)

        if adressconfigItem:
            self.setadressValue(qconfig.get(adressconfigItem))
            adressconfigItem.valueChanged.connect(self.setadressValue)

        # add switch button to layout
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.vBoxLayout.addLayout(self.hBoxlayout)

        StyleSheet.SET_CARD.apply(self)
        
        # Set size policies for better control
        self.PlainTextEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Adjust the layout to ensure no overlap
        self.hBoxlayout.setContentsMargins(10, 0, 10, 0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 10)

        self.setFixedSize(self.hBoxlayout.sizeHint().width(), self.vBoxLayout.sizeHint().height())
                          
    def __onCheckedChanged(self, isChecked: bool):
        """ switch button checked state changed slot """
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)
    def __onTextChanged(self):
        """ text edit text changed slot """
        ayyay=[]
        text = self.PlainTextEdit.toPlainText()
        if not text:
            return
        parts = text.split(",")
        for part in parts:
            while len(part) < 12:
                part = "0" + part
            if part not in ayyay:
                ayyay.append(part)
        self.setadressValue(ayyay)
    def setValue(self, isChecked: bool):
        if self.reportconfig:
            qconfig.set(self.reportconfig, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(
            self.tr('开') if isChecked else self.tr('关'))
    def setadressValue(self, adress: list):
        if self.adressConfig:
            qconfig.set(self.adressConfig, adress)
        str = ",".join(adress)
        self.PlainTextEdit.setPlainText(str)
    def setChecked(self, isChecked: bool):
        self.setValue(isChecked)

    def isChecked(self):
        return self.switchButton.isChecked()
    
class MultiReportSetingCard(QFrame):
    """ Connnect card """

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, ReportconfigItem: ConfigItem = None,
                 adressconfigItem: ConfigItem = None, parent=None):
        super().__init__(parent=parent)

        self.setObjectName('setting_card')
        self.iconLabel = IconWidget(icon, self)
        self.titleLabel = QLabel(title, self)
        self.hBoxLayout = QHBoxLayout()
        self.vBoxLayout = QVBoxLayout()
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(7, 0, 0, 0)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)

        self.hBoxLayout.addWidget(self.iconLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)

        self.hBoxLayout.addLayout(self.vBoxLayout)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignLeft)

        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)

        self.iconLabel.setFixedSize(16, 16)

        self.lhBoxLayout = QHBoxLayout(self)
        self.multireport = MultireportCard(icon, title, ReportconfigItem, adressconfigItem)

        self.lhBoxLayout.addLayout(self.hBoxLayout)
        self.lhBoxLayout.addWidget(self.multireport,0, Qt.AlignRight)
        self.setFixedHeight(self.multireport.height() + 15)
        StyleSheet.SET_CARD.apply(self)
    
    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        if isDarkTheme():
            painter.setBrush(QColor(255, 255, 255, 13))
            painter.setPen(QColor(0, 0, 0, 50))
        else:
            painter.setBrush(QColor(255, 255, 255, 170))
            painter.setPen(QColor(0, 0, 0, 19))

        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)   

class CheckUpgradeCard(SettingCard):
    """ Push setting card with primary color """

    def __init__(self, text, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.widget = QWidget(self)
        self.hBoxLayout.addWidget(self.widget, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button = QPushButton(text)
        self.button.setObjectName('primaryButton')
        self.update_thread = None
        self.ring = ProgressBar()
        # self.ring.setFixedWidth(self.widget.width())
        self.ring.setTextVisible(True)
        # self.ring.setVisible(False)
        self.ring.setRange(0, 100)
        self.button.setFixedWidth(82)
        self.process = QLabel()
        self.downlabel = QLabel()
        self.downlayout = QHBoxLayout()
        self.downlayout.addWidget(self.process)
        self.downlayout.addSpacing(10)
        self.downlayout.addWidget(self.ring)
        self.downlayout.addSpacing(10)
        self.downlayout.addWidget(self.downlabel)
        self.wqvBoxLayout = QVBoxLayout(self.widget)
        self.wqvBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.wqvBoxLayout.setContentsMargins(0,0,0,0)
        # self.wqvBoxLayout.addWidget(self.ring)
        # self.button.clicked.connect(self.__onAboutCardClicked)
        # signalBus.upgrade.connect(self.__onAboutCardClicked)

    def __onAboutCardClicked(self):
        if self.update_thread is not None and self.update_thread.isRunning():
            return
        # 创建工作线程实例
        self.update_thread = UpdateThread()
        # 连接信号和槽
        self.update_thread.update_signal.connect(self.update_ui)
        self.update_thread.process_info.connect(self.update_process_info)
        self.update_thread.update_info.connect(self.update_info)
        self.update_thread.start()
    
    def update_ui(self, result, msg, status):
        if result:
            InfoBar.success(
                msg,
                status,
                duration=1500,
                parent=self.window()
            )
        else:
            InfoBar.warning(
                msg,
                status,
                duration=1500,
                parent=self.window()
            )
        # signalBus.infopopup.emit(result, msg, status)
        if result is False:
            self.wqvBoxLayout.removeWidget(self.ring)
            self.update_thread.stop()
    def update_process_info(self, down, total, speed):
        if self.wqvBoxLayout.indexOf(self.downlayout) == -1:
            # downlayout尚未添加到wqvBoxLayout中
            self.wqvBoxLayout.addLayout(self.downlayout)
        self.ring.setVisible(True)
        progress_percentage = (down / total) * 100
        down = down / (1024 * 1024)
        total = total / (1024 * 1024)
        speed = speed / 1000.0
        self.process.setText(f"{progress_percentage:.2f}%")
        self.downlabel.setText(f"{down:.2f}M/{total:.2f}M  {speed:.2f}KB/s")
        self.ring.setValue(int(progress_percentage))
    
    def update_info(self, info, description):
        w = MessageBox(info, description, self.window())
        if w.exec():
            self.update_thread.update_enable.emit(True)
            print('Yes button is pressed')
        else:
            self.update_thread.update_enable.emit(False)
            print('Cancel button is pressed')

class SettingInterface(ScrollArea):
    """ Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("Settings"), self)

        self.connectPCGroup = SettingCardGroup(
            self.tr("连接设置"), self.scrollWidget)
            
        self.connectCard = ConnectCard(
            FIF.DOWNLOAD,
            self.tr("配置"),
            self.connectPCGroup
        )
        
        # music folders
        self.basicsetgroup = SettingCardGroup(
            self.tr("基础设置"), self.scrollWidget)
        
        self.logFolderCard = PushSettingCard(
            self.tr('选择文件夹'),
            FIF.DOWNLOAD,
            self.tr("日志文件夹"),
            cfg.get(cfg.logFolder),
            self.basicsetgroup
        )
        self.replayenableCard = SwitchSettingCard(
            Icon.REPLAY,
            self.tr('主动上报回复'),
            None,
            cfg.ReportReplay,
            self.basicsetgroup
        )
        self.regiongroup = ComboBoxSettingCard(
            cfg.Region,
            Icon.REGION,
            self.tr('省份'),
            None,
            texts=["南网","云南","广东","深圳","广西","贵州","海南","topo"],
            parent=self.basicsetgroup
        )
        self.multireport = MultiReportSetingCard(
            Icon.REGION,
            self.tr('多主站上报'),
            cfg.Multireport,
            cfg.MultireportAdress,
            parent=self.basicsetgroup
        )
        # personalization
        self.personalGroup = SettingCardGroup(
            self.tr('Personalization'), self.scrollWidget)
        self.micaCard = SwitchSettingCard(
            FIF.TRANSPARENT,
            self.tr('Mica effect'),
            self.tr('Apply semi transparent to windows and surfaces'),
            cfg.micaEnabled,
            self.personalGroup
        )
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr('Application theme'),
            self.tr("Change the appearance of your application"),
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('Use system setting')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("Interface zoom"),
            self.tr("Change the size of widgets and fonts"),
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                self.tr("Use system setting")
            ],
            parent=self.personalGroup
        )
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr('Language'),
            self.tr('Set your preferred language for UI'),
            texts=['简体中文', '繁體中文', 'English', self.tr('Use system setting')],
            parent=self.personalGroup
        )

        # material
        # self.materialGroup = SettingCardGroup(
        #     self.tr('Material'), self.scrollWidget)
        # self.blurRadiusCard = RangeSettingCard(
        #     cfg.blurRadius,
        #     FIF.ALBUM,
        #     self.tr('Acrylic blur radius'),
        #     self.tr('The greater the radius, the more blurred the image'),
        #     self.materialGroup
        # )

        # update software
        # self.updateSoftwareGroup = SettingCardGroup(
        #     self.tr("Software update"), self.scrollWidget)
        # self.updateOnStartUpCard = SwitchSettingCard(
        #     FIF.UPDATE,
        #     self.tr('Check for updates when the application starts'),
        #     self.tr('The new version will be more stable and have more features'),
        #     configItem=cfg.checkUpdateAtStartUp,
        #     parent=self.updateSoftwareGroup
        # )

        # # application
        # self.aboutGroup = SettingCardGroup(self.tr('About'), self.scrollWidget)
        # self.helpCard = HyperlinkCard(
        #     HELP_URL,
        #     self.tr('Open help page'),
        #     FIF.HELP,
        #     self.tr('Help'),
        #     self.tr(
        #         'Discover new features and learn useful tips about PyQt-Fluent-Widgets'),
        #     self.aboutGroup
        # )
        # self.feedbackCard = PrimaryPushSettingCard(
        #     self.tr('Provide feedback'),
        #     FIF.FEEDBACK,
        #     self.tr('Provide feedback'),
        #     self.tr('Help us improve PyQt-Fluent-Widgets by providing feedback'),
        #     self.aboutGroup
        # )
        # self.aboutCard = CheckUpgradeCard(
        #     self.tr('Check update'),
        #     FIF.INFO,
        #     self.tr('About'),
        #     '© ' + self.tr('Copyright') + f" {YEAR}, {AUTHOR}. " +
        #     self.tr('Version') + " " + VERSION,
        #     self.aboutGroup
        # )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('settingInterface')

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')
        StyleSheet.SETTING_INTERFACE.apply(self)

        self.micaCard.setEnabled(isWin11())
        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(36, 30)
        # add cards to group
        self.connectPCGroup.addSettingCard(self.connectCard)
        self.basicsetgroup.addSettingCard(self.logFolderCard)
        self.basicsetgroup.addSettingCard(self.replayenableCard)
        self.basicsetgroup.addSettingCard(self.regiongroup)
        self.basicsetgroup.addSettingCard(self.multireport)

        self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)
        self.personalGroup.addSettingCard(self.languageCard)

        # self.materialGroup.addSettingCard(self.blurRadiusCard)

        # self.updateSoftwareGroup.addSettingCard(self.updateOnStartUpCard)

        # self.aboutGroup.addSettingCard(self.helpCard)
        # self.aboutGroup.addSettingCard(self.feedbackCard)
        # self.aboutGroup.addSettingCard(self.aboutCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.connectPCGroup)
        self.expandLayout.addWidget(self.basicsetgroup)
        self.expandLayout.addWidget(self.personalGroup)
        # self.expandLayout.addWidget(self.materialGroup)
        # self.expandLayout.addWidget(self.updateSoftwareGroup)
        # self.expandLayout.addWidget(self.aboutGroup)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.success(
            self.tr('Updated successfully'),
            self.tr('Configuration takes effect after restart'),
            duration=1500,
            parent=self
        )

    def __onDownloadFolderCardClicked(self):
        """ download folder card clicked slot """
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), "./")
        if not folder or cfg.get(cfg.logFolder) == folder:
            return

        cfg.set(cfg.logFolder, folder)
        self.logFolderCard.setContent(folder)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        cfg.appRestartSig.connect(self.__showRestartTooltip)

        # music in the pc
        self.logFolderCard.clicked.connect(
            self.__onDownloadFolderCardClicked)

        # personalization
        self.themeCard.optionChanged.connect(lambda ci: setTheme(cfg.get(ci)))
        self.themeColorCard.colorChanged.connect(setThemeColor)
        self.micaCard.checkedChanged.connect(signalBus.micaEnableChanged)

        # about
        # self.feedbackCard.clicked.connect(
        #     lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL)))