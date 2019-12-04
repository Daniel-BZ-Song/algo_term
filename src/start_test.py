import time
import logging
import datetime
import trio
import urllib
from importlib import import_module
import asks
from asks import Session
from tradingclass import TradingEngine
from matchingengine.engine import MatchEngine
from marketdata.datadb import DataDB
from utils import Mode, ORDER_TYPE
from pymongo import MongoClient
from genalfa import Naive1, Naive2
import threading
from queue import Queue
import re

MESSAGE_QUEUE = Queue()

class MaketData(threading.Thread):
    def __init__(self, db_reader=None, group=None, target=None, name=None,
                 args=(), kwargs=None):
        super(MaketData, self).__init__()
        self.target = target
        self.name = name
        self.db_reader = db_reader
        self.pre_time = 0
        self.booked_trade = set()

    def run(self):
        for trade in self.db_reader.db_obj["trade.post"].find():
            trade_id = trade["trade_id"]
            if trade_id not in self.booked_trade:
                rest_flag = False
                dt_str = trade["time"].strip()
                if not dt_str:
                    continue
                dt = datetime.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                timestamp = time.mktime(dt.timetuple())
                if self.pre_time > 0:
                    rest_flag = (timestamp - self.pre_time) > 60
                    wait_time = max(0, timestamp - self.pre_time)
                    wait_time = min(1, wait_time/100)
                    time.sleep(wait_time)
                MESSAGE_QUEUE.put([trade, dt_str, rest_flag])
                self.pre_time = timestamp
                self.booked_trade.add(trade_id)

        MESSAGE_QUEUE.put(["done", "", ""])
        print("done")
        return

class Alfa(threading.Thread):
    def __init__(self, matching_engine=None,  stategy=None,
                 db_writer = None,
                 group=None, target=None, name=None,
                 args=(), kwargs=None):
        super(Alfa,self).__init__()
        self.target = target
        self.name = name
        self.matching_engine = matching_engine
        self.stategy = stategy
        self.db_writer = db_writer
        self.retry = 5
        return

    def process_book_reset(self, dt):
        print("reset book")
        book_rec = None
        regex = dt.split(".")[0][:-4]
        for _ in range(self.retry):
            if book_rec:
                break
            condition = {"timestamp": {"$regex": regex}}
            book_rec = self.db_writer.regex_find(condition, "book.post")
            regex = regex[:-1]


        self.matching_engine.init_book(book_rec, "ETH-USDT")
        self.stategy.remove_all_outstadning_order()
        for _, quotes in self.stategy.creat_requet().items():
            self.matching_engine.cancel_order(quotes)
                    
    def run(self):
        while True:
            if not MESSAGE_QUEUE.empty():
                trade, dt, rest_flag = MESSAGE_QUEUE.get()
                if trade == "done":
                    break
                if rest_flag:
                    self.process_book_reset(dt)

                order, trades = self.matching_engine.add_one_order(trade)
                position = self.stategy.process_market_trade(trades)
                if position:
                    top_bid = self.matching_engine.get_max_bid()
                    top_ask = self.matching_engine.get_max_ask()
                    print(f"Unrealized pnl: {self.stategy.get_current_unr_pnl(top_bid, top_ask)}  pnl: {self.stategy.get_current_pnl()}")
                    self.db_writer.write_data(self.stategy.name, position)

                self.stategy.data_reveiver(self.matching_engine.get_book(), time.time())
                for exec_type, quotes in self.stategy.creat_requet().items():
                    if exec_type == ORDER_TYPE.ORDER:
                        for order, trades in self.matching_engine.add_batch_order(quotes):
                            position = self.stategy.process(order, trades)
                    else: 
                         self.matching_engine.cancel_order(quotes)
        return


def setup_matching_engine(data_db):
    book_rec = data_db.get_first_data("book.post")
    mathing_engnine = MatchEngine()
    mathing_engnine.init_book(book_rec, "ETH-USDT")

    return mathing_engnine

def setup_alfa_engine(mathing_engnine):
    init_price = mathing_engnine.get_max_ask()
    alfa = Naive2(init_price=init_price)
    return alfa

def run():
    data_db = DataDB("market_data")
    data_db.start_client()

    mathing_engnine = setup_matching_engine(data_db)
    stategy = setup_alfa_engine(mathing_engnine)

    p = MaketData(name='producer',db_reader=data_db )
    c = Alfa(name='consumer', matching_engine=mathing_engnine, stategy=stategy, db_writer=data_db)

    p.start()
    c.start()


if __name__ == '__main__':
    run()