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

async def run():
    config = configparser.ConfigParser(strict=False)
    config.read("src/config/exchangeinfo.conf")
    trading = TradingEngine(None, datetime.date.today())
    marketDataMarker = MarketDataEngine(config)
    alfa = AlfaEngine(None, datetime.date.today())
    marketDataObjs = marketDataMarker.createMarketDataObjects()
    trading.addMarketDataEngine(marketDataObjs)
    trading.addAlfaEngine("test", alfa)

    await trading.getMarketData()
    print("done")

if __name__ == '__main__':
    trio.run(run)