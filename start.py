import time
import logging
import configparser
import trio
import urllib
from importlib import import_module
import asks
from asks import Session
from utils import TradingEngine, MarketDataEngine, AlfaEngine

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'log/okex_data_{time.time()}.log',
                    filemode='w')


async def run():
    config = configparser.ConfigParser(strict=False)
    config.read("config/exchangeinfo.conf")
    trading = TradingEngine(None)
    marketDataMarker = MarketDataEngine(config)
    alfa = AlfaEngine(None)
    marketDataObjs = marketDataMarker.createMarketDataObjects()
    trading.addMarketDataEngine(marketDataObjs)
    trading.addAlfaEngine("test", alfa)

    await trading.getMarketData()

if __name__ == '__main__':
    trio.run(run)