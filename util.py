class MarketDataEngine:
    def __init__(self, config):
        self.config = config

    def createMarketDataObjects(self):
        """create market data object from config
        """
        res = []
        for section in self.config.sections():
            log.info("Conf load: %s", section)
            module = import_module("marketdata.dataclass")
            inst = getattr(module, section)(**self.config[section])
            res.append(inst)

        return res

class TradingEngine:
    def  __init__(self, executionEngine):
        self.executionEngine = executionEngine
        self.alfaEngines = {}
        self.marketDataEngines = []

    def addAlfaEngine(self, engineName, engine):
        if engineName in self.alfaEngines:
            log.warning("Replace engine under name [%s] from [%s] to [%s]", engineName, self.alfaEngines[engineName].name, engine.name)
        self.alfaEngines[engineName] = engine

    def addMarketDataEngine(self, marketDataEngines):
        for engine in marketDataEngines:
            log.info("Adding market data %s", engine.endpoint_name)
            self.marketDataEngines.append(engine)

    async def grabberData(self, obj, send_channel, session):
        for url, header in obj.creatRequet():
            log.info(url)
            resp = await session.request("GET", url, header=header)
            rawData = resp.json()
            processedData = obj.process(rawData)
            await send_channel.send([obj.endpoint_name, processedData])

    async def getMarketData(self):
        session = Session()
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for markeDataEngine in self.marketDataEngines:
                nursery.start_soon(self.grabberData, markeDataEngine, send_channel, session)

            for name, alfaEngine in self.alfaEngines.items():
                log.info("Engine %s start", name)
                nursery.start_soon(alfaEngine.dataReceiver, receive_channel)

    async def getSingal(self):
        session = Session()
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for alfaEngine in self.alfaEngines:
                nursery.start_soon(alfaEngine.singal, send_channel)
            nursery.start_soon(self.executionEngine.receive, receive_channel, session)

class AlfaEngine:
    def __init__(self, strategy):
        self.strategy = strategy

    async def dataReceiver(self, receive_channel):
        while True:
            async for  endpoint_name, data in receive_channel:
                print(endpoint_name)
                print(data)
