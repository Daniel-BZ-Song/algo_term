import time
import logging
import trio
import asks
import csv
from asks import Session
from importlib import import_module
from utils import MissingEngineExcpetion, SessionWrap
from utils import Mode

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'log/trading_{time.time()}.log',
                    filemode='w')

          
class AlfaEngine:
    def __init__(self, strategy, date):
        self.strategy = strategy

    async def dataReceiver(self, receive_channel):
        async with receive_channel:
            async for endpoint_name, data in receive_channel:
                pass
                # if self.strategy.data_type == endpoint_name:
                #     self.strategy.data_reveiver(endpoint_name, data)

    async def singal(self, send_channel):
        self.strategy
        await send_channel.send([self.strategy.name, ])


class MarketDataEngine:
    def __init__(self, config):
        self.config = config

    def createMarketDataObjects(self):
        """create market data object from config
        """
        res = []
        for section in self.config.sections():
            module = import_module("marketdata.dataclass")
            class_name = self.config[section]["class"]
            inst = getattr(module, class_name)(**self.config[section])
            res.append(inst)

        return res

class TradingEngine:
    def  __init__(self, executionEngine, date, mode, data_db):
        self.executionEngine = executionEngine
        self.alfaEngines = {}
        self.marketDataEngines = []
        self.date = date
        self.db_obj = data_db
        self.mode = mode

    def addAlfaEngine(self, engineName, engine):
        if engineName in self.alfaEngines:
            print("replace")
        self.alfaEngines[engineName] = engine

    def addMarketDataEngine(self, marketDataEngines, ):
        for engine in marketDataEngines:
            self.marketDataEngines.append(engine)

    def validation(self):
        if not self.marketDataEngines:
             raise MissingEngineExcpetion("No market data engine")
        if not self.alfaEngines:
            raise MissingEngineExcpetion("No alfa engine")

    async def data_writer(self, receive_channel):
        import pandas as pd
        async with receive_channel:
            async for endpoint_name, data in receive_channel:
                self.db_obj.write_data(endpoint_name, data)
                
        log.info("done")

    async def grabberData(self, obj, send_channel, session):
        for url, header in obj.creatRequet():
            try:
                resp = await session.send_request("GET", url, header=header, timeout=2)
            except asks.errors.RequestTimeout:
                log.warning("%s time out", obj.endpoint_name)
                continue
            log.info(url)
            rawData = resp.json()
            processedData = obj.process(rawData)
            await send_channel.send([obj.endpoint_name, processedData])
        log.info("done")


    async def getMarketData(self):
        session = SessionWrap(data_db=self.db_obj,
                              mode=self.mode)
        self.validation()
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for markeDataEngine in self.marketDataEngines:
                nursery.start_soon(self.grabberData, markeDataEngine, send_channel, session)
            
            if self.mode != Mode.TEST:
                nursery.start_soon(self.data_writer, receive_channel)

            # for name, alfaEngine in self.alfaEngines.items():
            #     nursery.start_soon(alfaEngine.dataReceiver, receive_channel)

    async def getSingal(self):
        session = Session()
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for alfaEngine in self.alfaEngines:
                nursery.start_soon(alfaEngine.singal, send_channel)
            nursery.start_soon(self.executionEngine.receive, receive_channel, session)
