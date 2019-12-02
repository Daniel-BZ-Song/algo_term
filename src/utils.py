from asks import Session
import datetime
import os
import csv
from enum import Enum
from matchingengine.engine import MatchEngine

DATA_TYPE_LINE_BREAK = {"trade": "price",
                        "ticker": "ask",
                        "book": "ask"}

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
        data_db = kwargs.pop("data_db", None)
        if self.mode == Mode.TEST:
            self.respone = Respone(data_db)
            self.matching_engine = MatchEngine()

        super(SessionWrap, self).__init__(**kwargs)

    async def send_request(self, request_method, url, header, timeout):
        if self.mode == Mode.TEST:
            resp = self.respone.request(url)
        else:
            resp = await self.request(request_method, url, header=header, timeout=timeout)

        return resp

    async def send_order(self, order, request_method, url, header, timeout):
        if self.mode == Mode.TEST:
            resp = self.matching_engine.add_order(order)
        else:
            resp = await self.request(request_method, url, header=header, timeout=timeout)

        return resp
        