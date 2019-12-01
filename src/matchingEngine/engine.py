from decimal import Decimal
import orderbook.orderbook as orderbook


class MatchEngine:
    def __init__(self, ticker_size):
        self.book = orderbook.OrderBook(ticker_size)

    def backtest_