import time
import logging
import datetime
import configparser
import trio
import urllib
from importlib import import_module
import asks
from asks import Session
from tradingclass import TradingEngine, MarketDataEngine, AlfaEngine
from marketdata.datadb import DataDB
from utils import Mode

async def run():
    market_config = configparser.ConfigParser(strict=False)
    market_config.read("src/config/exchangeinfo.conf")
    marketDataMarker = MarketDataEngine(market_config)

    data_db = DataDB("market_data")
    data_db.start_client()

    trading = TradingEngine(None, datetime.date.today(), Mode.PROD, data_db)
    
    alfa = AlfaEngine(None, datetime.date.today())
    marketDataObjs = marketDataMarker.createMarketDataObjects()
    
    trading.addMarketDataEngine(marketDataObjs)
    trading.addAlfaEngine("test", alfa)

    await trading.getMarketData()
    print("done")

if __name__ == '__main__':
    trio.run(run)