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
from utils import Mode
from pymongo import MongoClient
from genalfa import Naive1

class MarketDataEngine:
    def __init__(self, config, mode):
        self.config = config
        self.mode = mode

    def gen_class_instance(self, section):
        module = import_module("marketdata.dataclass")
        class_name = self.config[section]["class"]
        inst = getattr(module, class_name)(**self.config[section])

        return inst

    def createMarketDataObjects(self):
        """create market data object from config
        """
        res = []
        if self.mode == Mode.TEST:
            res.append(self.gen_class_instance("TRADE"))
        else:
            for section in self.config.sections():
                res.append(self.gen_class_instance(section))
            

        return res


async def run():
    market_config = configparser.ConfigParser(strict=False)
    market_config.read("src/config/exchangeinfo.conf")
    marketDataMarker = MarketDataEngine(market_config, Mode.TEST)

    data_db = DataDB("market_data")
    data_db.start_client()

    trading = TradingEngine(datetime.date.today(), Mode.TEST, data_db)
    
    marketDataObjs = marketDataMarker.createMarketDataObjects()

    trading.addMarketDataEngine(marketDataObjs)


    await trading.get_market_data()

    print("done")

if __name__ == '__main__':
    trio.run(run)