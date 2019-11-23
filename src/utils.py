from asks import Session
import datetime
from refdata import CommunicationFlag
import os
import csv

DATA_TYPE_LINE_BREAK = {"trade": "price",
                        "ticker": "ask",
                        "book": "ask"}

class MissingEngineExcpetion(Exception):
    pass
 
class Respone:
    def __init__(self, start_date, end_date):
        self.date_type_mapping = {item: start_date for item in ["ticker", "book", "trade"]}
        self.end_date = end_date
        self.respon_date = {}
    
    def load_data(self, data_type, date):
        dataStr = date.strftime("%Y-%m-%d")
        file_path = f"data/{data_type}_{dataStr}.csv"
        if not os.path.exists(file_path):
            self.respon_date[data_type] = [CommunicationFlag.TEST_EOD]
        else:
            line_breaker = DATA_TYPE_LINE_BREAK[data_type]
            with open(file_path, "r") as fin:
                reader = csv.reader(fin)
                for line in reader:
                    if line_breaker in line:
                        header = line
                        self.respon_date[data_type].append(tmp)
                        tmp = []
                    else:
                        tmp.append(dict(zip(header, line)))

    def request(self, url):
        data_type = url.split("/")[-1]
        if not self.respon_date[data_type]:
            self.date_type_mapping[data_type] += datetime.timedelta(day=1)
            if self.date_type_mapping[data_type] > self.end_date:
                return CommunicationFlag.TEST_EOD

            self.load_data(data_type, self.date_type_mapping[data_type])

        return self.respon_date[data_type].pop()

class SessionWrap(Session):
    def  __init__(self, **kwargs):
        self.mode = kwargs.pop("mode", "prod")
        self.start_date = kwargs.pop("start_date", None)
        self.end_date = kwargs.pop("end_date", None)
        if self.mode == "back_test":
            self.load_back_test()
        super(SessionWrap, self).__init__(**kwargs)
    
    def load_back_test(self):
        self.respone = Respone(self.start_date, self.end_date)

    def send_request(self, url, header):
        if self.mode == "back_test":
            resp = self.respone.request(url)
        else:
            resp = self.request(self.mode, url, header=header)
        return resp
        