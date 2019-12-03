from decimal import Decimal
from lightmatchingengine.lightmatchingengine import LightMatchingEngine, Side
import logging
import time

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'log/matching_{time.time()}.log',
                    filemode='w')

class MatchEngine:
    def __init__(self):
        self.engine = LightMatchingEngine()
        self.instmt = ""

    def init_book(self, book, instmt):
        self.instmt = instmt
        for rec in book["asks"]:
            size = Decimal(rec[1])
            price = Decimal(rec[0])    
            self.engine.add_order(instmt, price, size, Side.SELL)

        for rec in book["bids"]:
            size = Decimal(rec[1])
            price = Decimal(rec[0])   
            self.engine.add_order(instmt, price, size, Side.BUY)

    def add_batch_order(self, batch):
        for order in batch:
            yield self.add_one_order(order)

    def add_one_order(self, quote):
        price = Decimal(quote["price"])
        size = Decimal(quote["size"])
        side = Side.BUY if quote["side"] == "buy" else Side.SELL

        try:
            order, trades = self.engine.add_order(self.instmt ,price, size, side)
        except (IndexError, AssertionError):
            print("Cross book")
            return None, []

        if trades:
            log.info("Order [%s] filled %s with %r", order.order_id, order.cum_qty, [t.order_id for t in trades])
        return order, trades

    def cancel_order(self, order_ids):
        for order_id in order_ids:
            del_order = self.engine.cancel_order(order_id, self.instmt )
            if del_order:
                log.info("Order [%s] cancelled for qty [%s] inst [%s]" , del_order.order_id, del_order.qty, del_order.instmt)  

            yield None, []

    def get_book(self):
        return self.engine.order_books[self.instmt]

    def is_cross_book(self, side, price):
        if side == Side.SELL:
            return self.get_max_bid() > price
        if side == Side.BUY:
            return price > self.get_max_ask()
         
    def get_max_bid(self):
        try:
            return [p for p in self.get_book().bids][0]
        except KeyError:
            return Decimal(0)

    def get_max_ask(self):
        try:
            return [p for p in self.get_book().asks][0]
        except KeyError:
            return Decimal(0)