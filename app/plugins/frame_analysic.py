import threading
import queue
from ..plugins.frame_csg import FrameCsg
from ..plugins.MeterTask import MeterTask
from ..plugins.frame_cco import FrameCCO
from ..plugins.frame_fun import FrameFun as frame_fun
from ..plugins import protocol
from ..common.signal_bus import signalBus
from typing import Union
from PyQt5.QtCore import Qt,QCoreApplication,pyqtSignal,QObject
from ..common.config import cfg
from ..plugins.frame_fun import CustomError,CustomMessageBox

class FrameProcessor(QObject):
    analisic_finish = pyqtSignal(dict)
    err_exception = pyqtSignal(CustomError)
    def __init__(self):
        super().__init__()
        self.frame_queue = queue.Queue()
        self.processing_thread = None
        self.running = False


    def process_frame(self, frame):
        try:
            frame_fun.globregion = cfg.get(cfg.Region)
            print(frame_fun.globregion)

            # Process the input text and generate the tree data
            show_data = []
            result = {}
            framedis = FrameCsg()
            meter_task = MeterTask()

            # Add tree data using add data function
            if protocol.is_dlt645_frame(frame):
                protocol.FRAME_645.Analysis_645_fram_by_afn(frame, show_data, 0)
            elif framedis.is_csg_frame(frame):
                framedis.Analysis_csg_frame_by_afn(frame, show_data, 0)
            elif meter_task.is_meter_task(frame):
                meter_task.analysic_meter_task(frame, show_data, 0)
            elif FrameCCO.is_cco_frame(frame):
                FrameCCO.Analysis_cco_frame_by_afn(frame, show_data, 0)
            
            result['报文'] = frame_fun.get_data_str_with_space(frame)
            result['结果'] = show_data

            self.analisic_finish.emit(result)
        except CustomError as e:
            print(e)
            self.err_exception.emit(e)
            result['报文'] = frame_fun.get_data_str_with_space(frame)
            result['结果'] = show_data

            self.analisic_finish.emit(result)
        except Exception as e:
            print(e)

    def worker(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)  # Timeout to allow checking self.running
                self.process_frame(frame)
                self.frame_queue.task_done()
            except queue.Empty:
                continue

    def start(self):
        self.running = True
        self.processing_thread = threading.Thread(target=self.worker)
        self.processing_thread.daemon = True  # This makes the thread exit when the main program exits
        self.processing_thread.start()

    def stop(self):
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()

    def add_frame(self, frame):
        self.frame_queue.put(frame)