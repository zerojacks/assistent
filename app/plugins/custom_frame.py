from asyncio.windows_events import ERROR_CONNECTION_ABORTED
from xml.dom.expatbuilder import FragmentBuilder
from ..plugins.frame_fun import FrameFun as frame_fun
from ..plugins.frame_fun import CustomError
from ..plugins.protocol import PraseFrameData, FRAME_645
from PyQt5.QtWidgets import QMessageBox
import re,threading
from datetime import datetime, timedelta
from enum import Enum
from ..common.config import ProtocolInfo,ConfigManager
from ..plugins import frame_csg


class custom_frame:
    def __init__(self):
        pass

    @staticmethod
    def task_data_frame(frame, dir, prm,task_result,start_pos):
        data_item_elem = None
        data_time=None
        prase_data = PraseFrameData()
        err = None
        sub_result = []
        data_segment = frame
        index = 0
        pos = 0
        num = 0
        length = len(data_segment)
        while pos < length:
            try:
                if frame_csg.guest_next_data_is_cur_item_data(data_item_elem, data_segment[pos:], data_time) == False:
                    DA = data_segment[pos:pos + 2]
                    item = data_segment[pos + 2: pos + 6]
                    data_item_elem,data_item = frame_csg.try_get_item_and_point(item, DA)
                    point_str = frame_csg.prase_DA_data(DA)
                    if data_item_elem is not None:
                        name = data_item_elem.find('name').text
                        dis_data_identifier = "数据标识编码：" + f"[{data_item}]" + "-" + name
                    else:
                        dis_data_identifier = "数据标识编码：" + f"[{data_item}]"
                    if dir == 1:#上行回复
                        frame_fun.add_data(task_result,f"<第{num + 1}组>信息点标识DA", frame_fun.get_data_str_with_space(DA), point_str, [index + pos, index + pos + 2])
                        pos += 2
                        frame_fun.add_data(task_result, f"<第{num + 1}组>数据标识编码DI",frame_fun.get_data_str_with_space(item),dis_data_identifier,[index + pos, index + pos + 4])
                        pos += 4
                    else:
                        frame_fun.add_data(sub_result,f"信息点标识DA", frame_fun.get_data_str_with_space(DA), point_str, [index + pos, index + pos + 2])
                        pos += 2
                        frame_fun.add_data(sub_result, f"数据标识编码DI",frame_fun.get_data_str_with_space(item),dis_data_identifier,[index + pos, index + pos + 4])
                        pos += 4

                item_data = []
                if data_item_elem is not None:
                    if dir == 1:#上行回复
                        sub_length_cont = data_item_elem.find('length').text
                        if sub_length_cont.upper() in "UNKNOWN":
                            sub_length = prase_data.caculate_item_length(data_item_elem, data_segment[pos:], ProtocolInfo.PROTOCOL_CSG13.name())
                            sub_datament = data_segment[pos:pos + sub_length]
                            new_datament = sub_datament
                        else:
                            sub_length = int(sub_length_cont)
                            sub_datament = data_segment[pos:pos + sub_length]
                            sub_length, new_datament = frame_csg.recaculate_sub_length(data_item_elem, sub_datament)
                        alalysic_result = prase_data.parse_data_item(data_item_elem,new_datament, index + pos, False, ProtocolInfo.PROTOCOL_CSG13.name())
                        frame_fun.prase_data_with_config(alalysic_result, False,item_data)
                    else:
                        sub_length = 0#下行读取报文
                else:
                    err = CustomError('未查找到数据标识：'+ data_item + '请检查配置文件！')
                    break

                if dir == 1:
                    frame_fun.add_data(task_result, f"<第{num + 1}组>数据内容",frame_fun.get_data_str_with_space(sub_datament),point_str[len("Pn="):] + "-" + dis_data_identifier[len("数据标识编码："):],[index + pos, index + pos + sub_length], item_data)
                    data_time = data_segment[pos + sub_length:pos + sub_length + 5]
                    time_str = frame_fun.parse_time_data(data_time, "YYMMDDhhmm", False)
                    frame_fun.add_data(task_result, f"<第{num + 1}组>数据时间",frame_fun.get_data_str_with_space(data_time),f"数据时间：" + time_str,[index + pos + sub_length,index + pos + sub_length + 5])
                    pos += 5
                else:
                    start_time = data_segment[pos:pos + 6]
                    end_time = data_segment[pos + 6:pos + 12]
                    data_dinsty = data_segment[pos + 12]
                    start_time_str = frame_fun.parse_time_data(start_time, "CCYYMMDDhhmm", False)
                    end_time_str = frame_fun.parse_time_data(end_time, "CCYYMMDDhhmm", False)
                    data_dinsty_str = frame_csg.get_data_dinsty(data_dinsty)
                    frame_fun.add_data(sub_result, f"数据起始时间",frame_fun.get_data_str_with_space(start_time),start_time_str,[index + pos, index + pos + 6])
                    frame_fun.add_data(sub_result, f"数据结束时间",frame_fun.get_data_str_with_space(end_time),end_time_str,[index + pos + 6, index + pos + 12])
                    frame_fun.add_data(sub_result, f"数据密度",f"{data_dinsty:02X}",f"数据间隔时间："+data_dinsty_str,[index + pos + 12, index + pos + 13])
                    pos += 13
                pos += sub_length
                num += 1
            except Exception as e:
                err = CustomError('解析数据失败！')
                break