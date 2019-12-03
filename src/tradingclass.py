import time
import logging
import trio
import asks
import csv
from asks import Session
from importlib import import_module
from utils import MissingEngineExcpetion, SessionWrap
from utils import Mode, RECEIVE_TYPE, ORDER_TYPE
from decimal import Decimal

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'log/trading_{time.time()}.log',
                    filemode='w')

class TradingEngine:
    def  __init__(self, date, mode, data_db):
        self.alfaEngines = {}
        self.market_data_engines = []
        self.date = date
        self.db_obj = data_db
        self.mode = mode
        self.strategy = None
        self.booked_trade = set()

    def addMarketDataEngine(self, market_data_engines):
        for engine in market_data_engines:
            self.market_data_engines.append(engine)

    def validation(self):
        if not self.market_data_engines:
             raise MissingEngineExcpetion("No market data engine")

    async def data_writer(self, receive_channel):
        async with receive_channel:
            async for endpoint_name, data in receive_channel:
                self.db_obj.write_data(endpoint_name, data)

    async def grab_data(self, obj, send_channel, session):
        for url, header in obj.creat_requet():
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

    async def get_market_data(self):
        session = SessionWrap(data_db=self.db_obj,
                              mode=self.mode)
        self.validation()
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for marke_data_engine in self.market_data_engines:
                nursery.start_soon(self.grab_data, marke_data_engine, send_channel, session)
            
            if self.mode != Mode.TEST:
                nursery.start_soon(self.data_writer, receive_channel)


           
            

            


