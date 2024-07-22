import threading
import serial
import socket, selectors
from ..common.commodule import CommType
from PyQt5.QtCore import QObject, pyqtSignal,QThread,pyqtSlot,QThreadPool,QRunnable,QTimer
import binascii,time
from enum import Enum
from ..common.signal_bus import signalBus
import re,datetime,os
from ..common.config import cfg
from ..common.trie import format_hex_string
from concurrent.futures import ThreadPoolExecutor
import logging
from PyQt5.QtNetwork import QTcpServer, QTcpSocket, QHostAddress,QAbstractSocket
from PyQt5.QtSerialPort import QSerialPort
import paho.mqtt.client as mqtt
import json
import sys
import asyncio
import threading
from bleak import BleakClient, BleakScanner
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QListWidget, QLineEdit, QTextEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

class SEND_ERR(Enum):
    SUCCESS = 0,
    ERR_TYPE = 1,
    ERR_LINK = 2,
    ERR_SEND = 3,

HEARTBEAT_INTERVAL = 10 # 每10秒发送一次心跳
MAX_MISSED_HEARTBEATS = 3 # 最大允许失踪的心跳数
class CommunicationError(Exception):
    pass
class WorkerSignals(QObject):
    finished = pyqtSignal()
    receive_data = pyqtSignal(QTcpSocket, bytes)
    send_data = pyqtSignal(QTcpSocket, bytes)

    def __init__(self):
        super().__init__()
        self.receive_data.connect(self.receive_data_slot)
    
    def receive_data_slot(self, socket, data: bytes):
        if isinstance(socket, QTcpSocket): 
            print(data, f'{socket.localAddress().toString()} {socket.localPort()}')
        
        signalBus.messagereceive.emit(socket,data)

    def send_data_slot(self, data: bytes):
        signalBus.sendmessage.emit(QTcpSocket, data)

class ClientWorker(QThread):
    disconnected = pyqtSignal(QTcpSocket, object)
    start_work = pyqtSignal()
    receive_data = pyqtSignal(QTcpSocket, bytes)
    data_sended = pyqtSignal(bytes)
    stopsingal = pyqtSignal()
    send_with_replay = pyqtSignal(bytes, bytes, int)

    """Worker that executes tasks in a thread."""
    def __init__(self, socket: QTcpSocket, parent=None):
        super().__init__(parent)
        self.socket = socket
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.disconnected.connect(self.on_disconnected)
        self.runingstatus = True
        self.loop_exited = False
        self.start_work.connect(self.on_start_work)
        self.data_sended.connect(self.send_data_to_client)
        self.stopsingal.connect(self.stop)

    def on_start_work(self):
        # worker内部处理开始逻辑
        self.run()
        
    def on_ready_read(self):
        data = self.socket.readAll()
        self.receive_data.emit(self.socket, data.data())
        print(data)

    def send_data_to_client(self, data: bytes):
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.write(data)
            signalBus.sendmessage.emit(self, data)
                
    def run(self):
        while self.runingstatus:
            # 在这里调用事件循环
            print("get event loop")
            self.exec_()
        print("loop exit")
        self.quit()
    def on_disconnected(self):
        self.disconnected.emit(self.socket, self)
        print("socket disconnected")
        self.stop()
    def stop(self):
        if self.runingstatus:
            # 在这里添加你的停止逻辑
            self.runingstatus = False
            self.socket.disconnected.disconnect(self.on_disconnected)
            self.socket.disconnectFromHost()
            self.quit()

class ClientWorkerRunnable(QRunnable):
    def __init__(self, socket: QTcpSocket, singals: WorkerSignals):
        super().__init__()
        self.socket = socket
        self.thread = QThread()
        self.worker = ClientWorker(self.socket)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker_start)
        self.worker.receive_data.connect(singals.receive_data)
        self.socket.disconnected.connect(self.disconnected_handler)
        singals.finished.connect(self.stop_work)
        self.isrun = True

    def worker_start(self):
        self.worker.start_work.emit()

    def run(self):
        print(f'{self.socket.peerAddress().toString()} ClientWorkerRunnable run')
        self.thread.start()
        self.thread.wait()
        print("ClientWorkerRunnable exit")

    def stop_work(self):
        if self.isrun:
            # 在这里添加你的停止逻辑
            print("ClientWorkerRunnable stop", self.thread.isRunning())
            self.isrun = False
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            print("ClientWorkerRunnable end", self.thread.isRunning())

    def disconnected_handler(self):
        signalBus.channel_disconnected.emit(CommType.TCP_SERVICE, self.worker)
        self.stop_work()


class TcpServer(QTcpServer):
    """TCP服务器"""
    err_event = pyqtSignal(int)
    tcpSocketChange = pyqtSignal(list)
    stopsingal = pyqtSignal()

    def __init__(self, ip_address, port, parent=None):
        super(TcpServer, self).__init__(parent)
        self.ip_address = ip_address
        self.port = port
        self.clients = []
        self.client_dic = {}
        self.threadpool = QThreadPool()
        self.singal = WorkerSignals()
        self.stop_requested = False
        self.stopsingal.connect(self.stop_server)

    def run(self):
        if self.isListening():
            print(f"Server is already listening on {self.ip_address}:{self.port}")
        else:
            if not self.listen(QHostAddress(self.ip_address), self.port):
                # 启动失败，发射连接异常信号
                self.err_event.emit(self.serverError())
            else:
                self.err_event.emit(255)
                print(f"Server listening on {self.ip_address}:{self.port}")

    def stop_server(self):
        self.stop_requested = True
        # 设置线程池中所有线程的标志位
        self.singal.finished.emit()
        self.threadpool.releaseThread()
        self.threadpool.waitForDone()
        self.threadpool.clear()
        self.clients.clear()
        self.client_dic.clear()
        self.err_event.emit(404)
        self.close()


    def incomingConnection(self, socketDescriptor):
        if self.stop_requested:
            return
        try:
            socket = QTcpSocket()
            socket.setSocketDescriptor(socketDescriptor)
            worker = ClientWorkerRunnable(socket, self.singal) 
            worker.worker.disconnected.connect(self.remove_client)
            self.threadpool.start(worker)
            self.clients.append(socket)
            self.client_dic[socket] = worker.worker 
            self.tcpSocketChange.emit(self.clients)
            signalBus.channel_connected.emit(CommType.TCP_SERVICE, worker.worker)
        except Exception as e:
            print(f"Error accepting connection: {e}")

    def handle_message_received(self, message):
        print(f"Received data: {message}")
        # 在这里处理接收到的数据，例如更新UI界面

    def send_message(self, message):
        for client in self.clients:
            client_handler = next(handler for handler in self.client_handlers if handler.client_socket == client)
            client_handler.send_message(message)

    def remove_client(self, client_socket: QTcpSocket, worker):
        print(f'{client_socket.peerAddress().toString()} removed')
        self.clients.remove(client_socket)
        self.client_dic.pop(client_socket)
        self.tcpSocketChange.emit(self.clients)
        signalBus.channel_disconnected.emit(CommType.TCP_SERVICE, worker)
    
    def get_socket_dic(self):
        return self.client_dic
    

class TcpClientWork(QThread):
    connected = pyqtSignal(QTcpSocket)
    err_event = pyqtSignal(int)
    data_received = pyqtSignal(bytes)
    data_sended = pyqtSignal(bytes)
    disconnected = pyqtSignal(QTcpSocket)
    try_connect = pyqtSignal()
    stopsingal = pyqtSignal()
    def __init__(self, host, port, singals: WorkerSignals):
        super().__init__()
        self.host = host
        self.port = port
        self.runingstatus = True
        self.singal = singals
        self.stop_requested = False
        self.socket = QTcpSocket()
        self.timeout_timer = QTimer()
        self.socket.disconnected.connect(self.disconnected_handler)
        self.socket.connected.connect(self.connected_handler)
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.error.connect(lambda: self.on_error(self.socket))
        self.singal.finished.connect(self.stop_client)
        self.try_connect.connect(self.run)
        self.data_sended.connect(self.send_data)

        self.timeout_timer.setInterval(3000)
        self.timeout_timer.timeout.connect(self.connection_timeout)
    def run(self):
        print(f"start to connect server {self.host}:{self.port}")
        self.socket.connectToHost(self.host, self.port)
        self.timeout_timer.start()
        while self.runingstatus:
            self.exec_()
        
        print("TcpClientWork quit")

    def stop_client(self):
        if self.runingstatus:
            self.runingstatus = False
            self.socket.disconnected.disconnect(self.disconnected_handler)
            self.socket.disconnectFromHost()
            self.socket.close()
            self.quit()  # 退出线程的事件循环
            self.wait()
            print("TcpClientWork stop")

    def on_ready_read(self):
        data = self.socket.readAll()
        self.data_received.emit(data.data())
        
    def connection_timeout(self):
        self.socket.abort()
        self.socket.close()
        self.timeout_timer.stop()
        self.err_event.emit(QAbstractSocket.SocketError.SocketTimeoutError)
        print("Connection timeout")

    def on_error(self, socket: QTcpSocket):
        err = socket.errorString()
        error_string_to_enum = {
            "Connection refused": QAbstractSocket.SocketError.ConnectionRefusedError,
            "Remote host closed": QAbstractSocket.SocketError.RemoteHostClosedError,
            "Host not found": QAbstractSocket.SocketError.HostNotFoundError,
            "Socket access error": QAbstractSocket.SocketError.SocketAccessError,
            "Socket resource error": QAbstractSocket.SocketError.SocketResourceError,
            "Connection timed out": QAbstractSocket.SocketError.SocketTimeoutError,
            "Datagram too large": QAbstractSocket.SocketError.DatagramTooLargeError,
            "Network error": QAbstractSocket.SocketError.NetworkError,
            "Address in use": QAbstractSocket.SocketError.AddressInUseError,
            "Socket address not available": QAbstractSocket.SocketError.SocketAddressNotAvailableError,
            "Unsupported socket operation": QAbstractSocket.SocketError.UnsupportedSocketOperationError,
            "Unfinished socket operation": QAbstractSocket.SocketError.UnfinishedSocketOperationError,
            "Proxy authentication required": QAbstractSocket.SocketError.ProxyAuthenticationRequiredError,
            "SSL handshake failed": QAbstractSocket.SocketError.SslHandshakeFailedError,
            "Proxy connection refused": QAbstractSocket.SocketError.ProxyConnectionRefusedError,
            "Proxy connection closed": QAbstractSocket.SocketError.ProxyConnectionClosedError,
            "Proxy connection timeout": QAbstractSocket.SocketError.ProxyConnectionTimeoutError,
            "Proxy not found": QAbstractSocket.SocketError.ProxyNotFoundError,
            "Proxy protocol error": QAbstractSocket.SocketError.ProxyProtocolError,
            "Operation error": QAbstractSocket.SocketError.OperationError,
            "SSL internal error": QAbstractSocket.SocketError.SslInternalError,
            "SSL invalid user data": QAbstractSocket.SocketError.SslInvalidUserDataError,
            "Temporary error": QAbstractSocket.SocketError.TemporaryError,
            "Unknown socket error": QAbstractSocket.SocketError.UnknownSocketError,
            "The remote host closed the connection": QAbstractSocket.SocketError.RemoteHostClosedError,
            "Network operation timed out": QAbstractSocket.SocketError.SocketTimeoutError,
            # Add more mappings as needed
        }

        error_code = error_string_to_enum.get(err, QAbstractSocket.SocketError.UnknownSocketError)      
        self.err_event.emit(error_code)
        print(err)
        if error_code == QAbstractSocket.SocketError.RemoteHostClosedError:
            self.disconnected.emit(socket)
            self.stop_client()  # 退出线程的事件循环

    def send_data(self, data):
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.write(data)
            self.socket.waitForBytesWritten()

    def disconnected_handler(self):
        self.disconnected.emit(self.socket)
        self.stop_client()  # 退出线程的事件循环
        print("client disconnected")
    def connected_handler(self):
        print("client connected")
        self.timeout_timer.stop()
        self.connected.emit(self.socket)
        self.err_event.emit(255)
        

class TcpClient(QThread):
    connected = pyqtSignal(QTcpSocket)
    err_event = pyqtSignal(int)
    data_received = pyqtSignal(bytes)
    data_sended = pyqtSignal(bytes)
    disconnected = pyqtSignal(QTcpSocket)
    stopsingal = pyqtSignal()
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.runingstatus = True
        self.stopsingal.connect(self.stop_client)
        self.singals = WorkerSignals()
        self.tcpthread = QThread()
        self.client = TcpClientWork(self.host, self.port, self.singals)
        self.client.moveToThread(self.tcpthread)
        self.tcpthread.started.connect(self.worker_start)
        self.client.connected.connect(self.connected_handler)
        self.client.err_event.connect(self.err_handler)
        self.client.data_received.connect(self.data_received_handler)
        self.client.disconnected.connect(self.disconnected_handler)
        self.data_sended.connect(self.data_send_handler)

    def worker_start(self):
        self.client.try_connect.emit()

    def run(self):
        self.tcpthread.start()
        while self.runingstatus:
            self.exec_()
        print("TcpClient run end")

    def stop_client(self):
        if self.runingstatus:
            self.runingstatus = False
            self.client.disconnected.disconnect(self.disconnected_handler)
            self.singals.finished.emit()
            self.quit()  # 退出线程的事件循环
            self.wait()
            self.err_event.emit(404)
            print("TcpClient stop end")
            
    def connected_handler(self, socket: QTcpSocket):
        self.connected.emit(socket)
        signalBus.channel_connected.emit(CommType.TCP_CLIENT, self)

    def err_handler(self, err_code):
        self.err_event.emit(err_code)
    
    def data_send_handler(self, data):
        self.client.data_sended.emit(data)
        signalBus.sendmessage.emit(self, data)

    def data_received_handler(self, data):
        self.data_received.emit(data)

    def disconnected_handler(self, socket: QTcpSocket):
        self.disconnected.emit(socket)
        signalBus.channel_disconnected.emit(CommType.TCP_CLIENT, self)

class SerialPortManager(QObject):
    err_event = pyqtSignal(int)
    data_received = pyqtSignal(bytes)
    data_sended = pyqtSignal(bytes)
    start_signal = pyqtSignal()
    connected = pyqtSignal(QSerialPort)
    disconnected = pyqtSignal(QSerialPort)

    def __init__(self, port_name, baud_rate, check_bit, data_bit, stop_bit, timeout=5000):
        super().__init__()

        self.port_name = port_name
        self.baud_rate = baud_rate
        self.check_bit = check_bit
        self.data_bit = data_bit
        self.stop_bit = stop_bit
        self.timeout = timeout
        self.serial_port = QSerialPort()
        self.serial_port.setPortName(self.port_name)
        self.serial_port.setBaudRate(self.baud_rate)
        self.serial_port.setParity(self.check_bit)
        self.serial_port.setDataBits(self.data_bit)
        self.serial_port.setStopBits(self.stop_bit)
        self.serial_port.readyRead.connect(self.read_data)
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setInterval(timeout)
        self.timeout_timer.timeout.connect(self.connection_timeout)
        self.serial_port.errorOccurred.connect(self.err_handler)
        self.start_signal.connect(self.open_port)
        self.data_sended.connect(self.send_data)
        QSerialPort.SerialPortError
    def open_port(self):
        print("open port")
        if not self.serial_port.isOpen():
            self.timeout_timer.start()
            if self.serial_port.open(QSerialPort.ReadWrite):
                self.timeout_timer.stop()
                self.err_event.emit(255)
                self.connected.emit(self.serial_port)
                print("open port success")
                return True
            else:
                print("open port Failed.")
                return False
        else:
            print("Serial port is already open.")
            return False

    def close_port(self):
        self.disconnected.emit(self.serial_port)
        if self.serial_port.isOpen():
            self.serial_port.close()
            print("Serial port closed.")
            return True
        else:
            print("Serial port is already closed.")
            return False

    def send_data(self, data):
        if self.serial_port.isOpen():
            self.serial_port.write(data)
            signalBus.sendmessage.emit(self, data)
            print(f"Sent data: {data}")
        else:
            print("Serial port is not open.")

    def read_data(self):
        data = self.serial_port.readAll().data()
        print(f"Received data: {data}")
        self.data_received.emit(data)
        signalBus.messagereceive.emit(self, data)

    def connection_timeout(self):
        print("Connection timed out.")
        self.close_port()
        self.timeout_timer.stop()
        # self.err_event.emit(1)

    def err_handler(self, err):
        if err != QSerialPort.SerialPortError.NoError:
            print(f"Error occurred: {err}")
            self.timeout_timer.stop()
            self.err_event.emit(err)

class SerialPortThread(QThread):
    connected = pyqtSignal(QSerialPort)
    err_event = pyqtSignal(int)
    data_received = pyqtSignal(bytes)
    data_sended = pyqtSignal(bytes)
    disconnected = pyqtSignal(QSerialPort)
    stopsingal = pyqtSignal()
    def __init__(self, port_name, baud_rate, check_bit, data_bits, stop_bits):
        super().__init__()
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.check_bit = check_bit
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.runingstatus = True
        self.serial_manager = SerialPortManager(self.port_name, self.baud_rate, self.check_bit, self.data_bits, self.stop_bits)
        self.stopsingal.connect(self.stop_serial_manager)
        self.serial_manager.connected.connect(self.connected)
        self.serial_manager.disconnected.connect(self.disconnected)
        self.serial_manager.data_received.connect(self.data_received)
        self.serial_manager.err_event.connect(self.err_event)
        self.serial_manager.connected.connect(self.connected_handler)
        self.disconnected.connect(self.disconnected_handler)
        self.data_sended.connect(self.serial_manager.data_sended)

    def run(self):
        self.serial_manager.start_signal.emit()
        while self.runingstatus:
            self.exec_()

        print("SerialPortThread run end")
        # You can add more serial port operations here...

    def data_send(self, data):
        self.serial_manager.data_sended(data)
        signalBus.sendmessage.emit(self, data)

    def stop_serial_manager(self):
        if self.runingstatus:
            self.runingstatus = False
            self.serial_manager.close_port()
            self.quit()
            self.wait()
            self.err_event.emit(404)
    
    def connected_handler(self, serial: QSerialPort):
        signalBus.channel_connected.emit(CommType.SERIAL, self)
    
    def disconnected_handler(self, serial: QSerialPort):
        signalBus.channel_disconnected.emit(CommType.SERIAL, self)

class pahoMqttClient():
    """paho mqtt客户端"""
    err_event = pyqtSignal(int)
    data_received = pyqtSignal(bytes)
    data_sended = pyqtSignal(bytes)
    start_signal = pyqtSignal()
    connected = pyqtSignal(QSerialPort)
    disconnected = pyqtSignal(QSerialPort)

    def __init__(self, callback_api_version=mqtt.CallbackAPIVersion.VERSION2):  
        super().__init__()                       
        # MQTT回调函数
        print("pahoMqttClient init start")
        self.client = mqtt.Client(callback_api_version=callback_api_version)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.on_connect_callback = None
        self.on_message_callback = None
        self.on_timeout_callback = None
        #定时器
        self.timer = None
        print("pahoMqttClient init")

    # 注册连接回调函数
    def registerConnectCallBack(self, on_connect_callback):
        self.on_connect_callback = on_connect_callback

    # 注册消息回调函数
    def registerRecvMsgCallBack(self, on_message_callback):
        self.on_message_callback = on_message_callback

    # 注册超时回调函数
    def registerTimeoutCallBack(self, on_timeout_callback):
        self.on_timeout_callback = on_timeout_callback      
    def username_pw_set(self,username, password):
        self.client.username_pw_set(username, password)
    # 连接MQTT服务器回调函数
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.on_connect_callback is not None:
            # 调用外部定义的回调函数
            self.on_connect_callback(client, userdata, flags, reason_code, properties)

    # 消息接收回调函数
    def on_message(self, client, userdata, msg):
        if self.on_message_callback is not None:
            # 调用外部定义的回调函数
            self.on_message_callback(client, userdata, msg)

    # 超时回调函数
    def on_timeout(self):
        if self.on_timeout_callback is not None:
            # 调用外部定义的回调函数
            self.on_timeout_callback()

    # 启动定时器
    def startTimer(self, second):
        self.timer = threading.Timer(second, self.on_timeout)
        self.timer.start()

    # 停止定时器
    def stopTimer(self):
        self.timer.cancel()

    # 连接MQTT服务器
    def connect(self, broker = '127.0.0.1', port = 1883, username = "", passwd = ""):
        print("MQTTClientThread connect", broker, port, username, passwd)
        self.client.username_pw_set(username, passwd)
        self.client.connect(broker, port, 60)
        self.client.loop_start()

    # 判断连接状态 
    def isConnected(self):
        return self.client.is_connected()

    # 主题订阅
    def subscribe(self, topic):
        self.client.subscribe(topic)

    # 取消订阅
    def unsubscribe(self, topic):
        self.client.unsubscribe(topic)

    # 消息发布
    def publish(self, topic, message):
        self.client.publish(topic, message)

    # 断开连接MQTT服务器
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

class MqttMessageDetails:
    def __init__(self, topic, payload, qos, retain):
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain

class MQTTClientThread(QThread):
    connected = pyqtSignal(pahoMqttClient)
    err_event = pyqtSignal(int)
    message_received = pyqtSignal(MqttMessageDetails)
    message_published = pyqtSignal(str, str)
    disconnected = pyqtSignal(pahoMqttClient)
    stopsingal = pyqtSignal()

    def __init__(self, broker_address, broker_port, username=None, password=None, topic='#'):
        super().__init__()
        self.client = pahoMqttClient()
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.registerConnectCallBack(self.on_connect)
        self.client.registerRecvMsgCallBack(self.on_message)
        self.client.registerTimeoutCallBack(self.on_timeout)
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.broker_name = username
        self.broker_password = password
        self.running = False
        self.stopsingal.connect(self.stop)
        self.deftopic = topic
        self.message_published.connect(self.publish_message)
    def get_def_topic(self):
        return self.deftopic
    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(self.deftopic)
        self.err_event.emit(255)
        self.connected.emit(self.client)
        signalBus.channel_connected.emit(CommType.MQTT, self)

    def on_message(self, client, userdata, msg):
        payload = msg.payload
        print(f"Received message on topic {msg.topic}: {payload}")
        try:
            message_details = MqttMessageDetails(
                    topic=msg.topic,
                    payload=msg.payload.decode('utf-8'),
                    qos=msg.qos,
                    retain=msg.retain
                )
        except Exception as e:
            print("on_message exception", e)
            message_details = MqttMessageDetails(
                    topic=msg.topic,
                    payload=msg.payload,
                    qos=msg.qos,
                    retain=msg.retain
            )
        self.message_received.emit(message_details)    
    def publish_message(self, topic, message):
        self.client.publish(topic, message)

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def unsubscribe(self, topic):
        self.client.unsubscribe(topic)
    def on_timeout(self):
        print("连接超时")
        self.err_event.emit(100)

    def run(self):
        if self.running:
            return
        self.running = True
        print("MQTTClientThread start")
        try:
            self.client.connect(self.broker_address, self.broker_port)
        except Exception as e:
            print("MQTTClientThread connect exception", e)
            self.err_event.emit(100)
            return
        while self.running:
            self.msleep(100)  # 在这里加入一个短暂的睡眠以减小 CPU 使用
        
        print("MQTTClientThread end")
        # self.client.disconnect()

    def stop(self):
        if self.running:
            self.running = False
            self.client.disconnect()
            self.quit()
            self.wait()
            self.err_event.emit(404)
            print("MQTTClientThread stop end")

class BLEWorker(QThread):
    devices_discovered = pyqtSignal(list)
    services_discovered = pyqtSignal(list)
    data_received = pyqtSignal(bytes)
    connection_status = pyqtSignal(bool)
    stopsignal = pyqtSignal()
    data_sended = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()
        self.client = None
        self.address = None
        self.loop = asyncio.new_event_loop()
        self.connection_event = threading.Event()
        self.characteristic_uuid = None
        self.stopsignal.connect(self.disconnect_device)
        self.data_sended.connect(self.handle_send_data)

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def scan_devices(self):
        devices = await BleakScanner.discover()
        self.devices_discovered.emit(devices)

    async def connect_device(self, address):
        self.client = BleakClient(address)
        self.address = address
        try:
            await self.client.connect()
            services = self.client.services
            services_info = self.process_services(services)
            self.services_discovered.emit(services_info)
            self.connection_status.emit(True)
            print("BLE connected client:", self.client)
            self.connection_event.set()
            signalBus.channel_connected.emit(CommType.BLUETOOTH, self)
        except Exception as e:
            print(e)
            self.connection_status.emit(False)

    async def disconnect_device(self):
        if self.client and self.client.is_connected:
            try:
                # 停止所有通知
                print("BLE disconnect start")
                await self.client.stop_notify(self.characteristic_uuid)
                print("BLE stop_notify")
                await self.client.disconnect()
                self.connection_status.emit(False)
                print("BLE disconnected")
                self.connection_event.clear()
                signalBus.channel_disconnected.emit(CommType.BLUETOOTH, self)
            except Exception as e:
                print(f"Error during disconnection: {e}")
                self.connection_status.emit(False)

    async def set_characteristic_uuid(self, uuid):
        try:
            self.characteristic_uuid = uuid
            await self.client.start_notify(uuid, self.notification_handler)
        except Exception as e:
            print(e)

    def process_services(self, services):
        services_info = []
        for service in services:
            characteristics = [
                {
                    'uuid': char.uuid,
                    'description': char.description
                }
                for char in service.characteristics
            ]
            services_info.append({
                'uuid': service.uuid,
                'description': service.description,
                'characteristics': characteristics
            })
        return services_info
    
    def notification_handler(self, sender, data):
        print("ble receive data", sender, data)
        self.data_received.emit(bytes(data))

    def handle_send_data(self, data):
        asyncio.run_coroutine_threadsafe(self.send_data(data), self.loop)

    async def send_data(self, data):
        if self.client and self.client.is_connected:
            try:
                print("BLE send data \n", self.characteristic_uuid, data)
                await self.client.write_gatt_char(self.characteristic_uuid, data)
            except Exception as e:
                print(f"Error in send_data: {e}")
        else:
            print("Client is not connected or is None.")