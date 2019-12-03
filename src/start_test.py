import time
import logging
import datetime
import configparser
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
from genalfa import Naive1
import threading
from queue import Queue

MESSAGE_QUEUE = Queue()

class MaketData(threading.Thread):
    def __init__(self, db_reader=None, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(MaketData,self).__init__()
        self.target = target
        self.name = name
        self.db_reader = db_reader
        self.pre_time = 0
        self.booked_trade = set()

    def run(self):
        for trade in self.db_reader.db_obj["trades.posts"].find():
            trade_id = trade["trade_id"]
            if trade_id not in self.booked_trade:
                dt = trade["time"]
                dt = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%fZ')
                timestamp = time.mktime(dt.timetuple())
                #print("market: ", trade["price"], trade["side"],  trade["size"], trade_id)
                if self.pre_time > 0:
                    wait_time = max(0, timestamp - self.pre_time)
                    wait_time = min(1, wait_time/100)
                    time.sleep(wait_time)
                MESSAGE_QUEUE.put(trade)
                self.pre_time = timestamp
                self.booked_trade.add(trade_id)

        MESSAGE_QUEUE.put("done")
        print("done")
        return

class Alfa(threading.Thread):
    def __init__(self, matching_engine=None,  stategy=None,
                 db_writer = None,
                 group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(Alfa,self).__init__()
        self.target = target
        self.name = name
        self.matching_engine = matching_engine
        self.stategy = stategy
        self.db_writer = db_writer
        return

    def run(self):
        while True:
            if not MESSAGE_QUEUE.empty():
                trade = MESSAGE_QUEUE.get()
                if trade == "done":
                    break
                order, trades = self.matching_engine.add_one_order(trade)
                position = self.stategy.process_market_trade(trades)
                if position:
                    print(f"got something\n {position}")
                    self.db_writer.write_data(self.stategy.name, position)
                self.stategy.data_reveiver(self.matching_engine.get_book(), time.time())
                for exec_type, quotes in self.stategy.creat_requet().items():
                    if exec_type == ORDER_TYPE.ORDER:
                        for order, trades in self.matching_engine.add_batch_order(quotes):
                            position = self.stategy.process( order, trades)
                            #if order:
                                #print("our: ", order.price, order.side)
                            # if position:
                            #     print(f"got something\n {position}")
                            #     self.db_writer.write_data(self.stategy.name, position)
                    else: 
                         self.matching_engine.cancel_order(quotes)
        return


def setup_matching_engine(data_db):
    book_rec = data_db.get_first_data("book.posts")
    mathing_engnine = MatchEngine()
    mathing_engnine.init_book(book_rec, "ETH-USDT")

    return mathing_engnine

def setup_alfa_engine():
    alfa = Naive1()
    return alfa

def run():
    data_db = DataDB("market_data")
    data_db.start_client()

    mathing_engnine = setup_matching_engine(data_db)
    stategy = setup_alfa_engine()

    p = MaketData(name='producer',db_reader=data_db )
    c = Alfa(name='consumer', matching_engine=mathing_engnine, stategy=stategy, db_writer=data_db)

    p.start()
    c.start()


if __name__ == '__main__':
    run()