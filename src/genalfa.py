from queue import Queue

class Strategy:
    def data_reveiver(self, data):
        raise NotImplementedError()

    def get_singal(self):
        raise NotImplementedError()

class Naive1(Strategy):
    name = "naive1"

    def __init__(self):
        self.target_buy_price = Queue()
        self.target_sell_price = Queue()
        self.volume = 0.0025

    def data_reveiver(self, book):
        self.target_buy_price.put(book["bids"][0][0])
        self.target_buy_price.put(book["bids"][1][0])
        self.target_sell_price.put(book["asks"][0][0])
        self.target_sell_price.put(book["asks"][1][0])

    def get_singal(self):
        while self.target_buy_price.empty():
            price = self.target_buy_price.get()
            yield {"price": price, "size": self.volume , "side": "buy", "type": "limit"}

        while self.target_sell_price.empty():
            price = self.target_sell_price.get()
            yield {"price": price, "size": self.volume , "side": "sell", "type": "limit"}
