from asks import Session
import datetime
import os
import csv
from enum import Enum

DATA_TYPE_LINE_BREAK = {"trade": "price",
                        "ticker": "ask",
                        "book": "ask"}

class RECEIVE_TYPE(Enum):
    NO_DATA = "no data"

class ORDER_TYPE(Enum):
    CANCEL = "cancel"
    ORDER = "order"
class CommunicationFlag(Enum):
    TEST_EOD = "EOD"
    
class Mode(Enum):
    PROD = "prod"
    TEST = "back_test"

class MissingEngineExcpetion(Exception):
    pass
 
class FakeJson:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    
class Respone:
    def __init__(self, data_db):
        self.data_db = data_db
        self.data_mapping = {}

    def request(self, url):
        data_type = url.split("/")[-1]
        if data_type not in self.data_mapping:
            self.data_mapping[data_type] = self.data_db.get_data(data_type)
        data = next(self.data_mapping[data_type])
        return FakeJson(data)

class SessionWrap(Session):
    """Enable to process back test requests 
    """
    def  __init__(self, **kwargs):
        self.mode = kwargs.pop("mode", "prod")
        self.start_date = kwargs.pop("start_date", None)
        self.end_date = kwargs.pop("end_date", None)
        self.data_db = kwargs.pop("data_db", None)
        if self.mode == Mode.TEST:
            self.respone = Respone(self.data_db)
            self.exection_engine = kwargs.pop("matching_engine", None)

        super(SessionWrap, self).__init__(**kwargs)

    async def send_request(self, request_method, data, header, timeout):
        if self.mode == Mode.TEST:
            resp = self.respone.request(data)
        else:
            resp = await self.request(request_method, data, header=header, timeout=timeout)

        return resp

    async def send_order(self, orders):
        res = []
        for order_type, orders_info in orders.items():
            if order_type == ORDER_TYPE.ORDER:
                for order in orders_info:
                    return_value = self.exection_engine.add_order(order)
            elif order_type == ORDER_TYPE.CANCEL:
                for order_id in orders_info:
                    return_value = self.exection_engine.cancel_order(order_id, "ETH-USDT")

            res.append(return_value)

        return res