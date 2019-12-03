from utils import ORDER_TYPE

class Execution:
    def __init__(self, mode):
        self.mode = mode

    def receive(self, receive_channel, alfaEngine, session):
         async with receive_channel:
            async for orders in receive_channel:
                order, trades = await session.send_order(orders, session)
                alfaEngine.
                session.write_data()
                