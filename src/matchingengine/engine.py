from decimal import Decimal
import orderbook.orderbook as orderbook
import logging
import time

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'log/matching_{time.time()}.log',
                    filemode='w')


class MatchEngine:
    def __init__(self, ticker_size):
        self.book = orderbook.OrderBook(ticker_size)

    def add_order(self, order):
        _, order_id = self.book.process_order(order, False, True)
        log.info("Insert a new order %s", order_id)
        
        return order_id
        

