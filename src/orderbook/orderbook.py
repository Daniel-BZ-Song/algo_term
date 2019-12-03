import sys
import math
from collections import deque # a faster insert/pop queue
try:
    from StringIO import StringIO ## for Python 2
except ImportError:
    from io import StringIO ## for Python 3

from .ordertree import OrderTree
from decimal import Decimal

class OrderBookException(Exception):
    pass

class OrderBook(object):
    def __init__(self, tick_size = 0.0001):
        self.tape = deque(maxlen=None) # Index[0] is most recent trade
        self.bids = OrderTree()
        self.asks = OrderTree()
        self.last_tick = None
        self.last_timestamp = 0
        self.tick_size = tick_size
        self.time = 0
        self.next_order_id = 0

    def clip_price(self, price):
        '''Clips the price according to the tick size. May not make sense if not 
        a currency'''
        return round(price, int(math.log10(1 / self.tick_size)))

    def update_time(self):
        self.time += 1

    def process_order(self, quote, from_data, verbose):
        order_type = quote['type']
        size = quote['size']
        price = quote['price']
        order_in_book = None
        if from_data:
            self.time = quote['timestamp']
        else:
            self.update_time()
            quote['timestamp'] = self.time
        if size <= Decimal(0):
            sys.exit('process_order() given order of size <= 0')
        if not from_data:
            self.next_order_id += 1
        if order_type == 'market':
            trades = self.process_market_order(quote, verbose)
        elif order_type == 'limit':
            price = self.clip_price(price)
            trades, order_in_book = self.process_limit_order(quote, from_data, verbose)
        else:
            sys.exit("order_type for process_order() is neither 'market' or 'limit'")
        return trades, order_in_book

    def process_order_list(self, side, order_list, size_still_to_trade, quote, verbose):
        '''
        Takes an OrderList (stack of orders at one price) and an incoming order and matches
        appropriate trades given the order's size.
        '''
        trades = []
        size_to_trade = size_still_to_trade
        while len(order_list) > 0 and size_to_trade > 0:
            head_order = order_list.get_head_order()
            traded_price = head_order.price
            counter_party = head_order.trade_id
            if size_to_trade < head_order.size:
                traded_size = size_to_trade
                # Do the transaction
                new_book_size = head_order.size - size_to_trade
                head_order.update_quantity(new_book_size, head_order.timestamp)
                size_to_trade = 0
            elif size_to_trade == head_order.size:
                traded_size = size_to_trade
                if side == 'buy':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                size_to_trade = 0
            else: # size to trade is larger than the head order
                traded_size = head_order.size
                if side == 'buy':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                size_to_trade -= traded_size
            if verbose:
                print (f"TRADE: Time - {self.time}, Price - {traded_price}, size - {traded_size}, TradeID - {quote['trade_id']}")
            transaction_record = {
                    'timestamp': self.time,
                    'price': traded_price,
                    'size': traded_size,
                    'time': self.time
                    }

            if side == 'buy':
                transaction_record['party1'] = [counter_party, 'buy', head_order.order_id]
                transaction_record['party2'] = [quote['trade_id'], 'sell', None]
            else:
                transaction_record['party1'] = [counter_party, 'sell', head_order.order_id]
                transaction_record['party2'] = [quote['trade_id'], 'buy', None]

            self.tape.append(transaction_record)
            trades.append(transaction_record)
        return size_to_trade, trades
                    
    def process_market_order(self, quote, verbose):
        trades = []
        size_to_trade = quote['size']
        side = quote['side']
        if side == 'buy':
            while size_to_trade > 0 and self.asks:
                best_price_asks = self.asks.min_price_list()
                size_to_trade, new_trades = self.process_order_list('sell', best_price_asks, size_to_trade, quote, verbose)
                trades += new_trades
        elif side == 'sell':
            while size_to_trade > 0 and self.bids:
                best_price_bids = self.bids.max_price_list()
                size_to_trade, new_trades = self.process_order_list('buy', best_price_bids, size_to_trade, quote, verbose)
                trades += new_trades
        else:
            sys.exit('process_market_order() recieved neither "bid" nor "ask"')
        return trades

    def process_limit_order(self, quote, from_data, verbose):
        order_in_book = None
        trades = []
        size_to_trade = Decimal(quote['size'])
        side = quote['side']
        price = quote['price']
        if side == 'buy':
            while (self.asks and price > self.asks.min_price() and size_to_trade > 0):
                best_price_asks = self.asks.min_price_list()
                size_to_trade, new_trades = self.process_order_list('sell', best_price_asks, size_to_trade, quote, verbose)
                trades += new_trades
            # If volume remains, need to update the book with new size
            if size_to_trade > 0:
                if not from_data:
                    quote['order_id'] = self.next_order_id
                quote['size'] = size_to_trade
                self.bids.insert_order(quote)
                order_in_book = quote
        elif side == 'sell':
            while (self.bids and price < self.bids.max_price() and size_to_trade > 0):
                best_price_bids = self.bids.max_price_list()
                size_to_trade, new_trades = self.process_order_list('buy', best_price_bids, size_to_trade, quote, verbose)
                trades += new_trades
            # If volume remains, need to update the book with new size
            if size_to_trade > 0:
                if not from_data:
                    quote['order_id'] = self.next_order_id
                quote['size'] = size_to_trade
                self.asks.insert_order(quote)
                order_in_book = quote
        else:
            raise OrderBookException('process_limit_order() given neither "bid" nor "ask"')
        
        return trades, order_in_book

    def cancel_order(self, side, order_id, time=None):
        if time:
            self.time = time
        else:
            self.update_time()
        if side == 'buy':
            if self.bids.order_exists(order_id):
                self.bids.remove_order_by_id(order_id)
        elif side == 'sell':
            if self.asks.order_exists(order_id):
                self.bids.remove_order_by_id(order_id)
        else:
            sys.exit('cancel_order() given neither "bid" nor "ask"')

    def modify_order(self, order_id, order_update, time=None):
        if time:
            self.time = time
        else:
            self.update_time()
        side = order_update['side']
        order_update['order_id'] = order_id
        order_update['timestamp'] = self.time
        if side == 'buy':
            if self.bids.order_exists(order_update['order_id']):
                self.bids.update_order(order_update)
        elif side == 'sell':
            if self.asks.order_exists(order_update['order_id']):
                self.asks.update_order(order_update)
        else:
            sys.exit('modify_order() given neither "bid" nor "ask"')

    def get_volume_at_price(self, side, price):
        price = self.clip_price(price)
        if side == 'buy':
            volume = 0
            if self.bids.price_exists(price):
                volume = self.bids.get_price(price).volume
            return volume
        elif side == 'sell':
            volume = 0
            if self.asks.price_exists(price):
                volume = self.asks.get_price(price).volume
            return volume
        else:
            sys.exit('get_volume_at_price() given neither "bid" nor "ask"')

    def get_best_bid(self):
        return self.bids.max_price()

    def get_worst_bid(self):
        return self.bids.min_price()

    def get_best_ask(self):
        return self.asks.min_price()

    def get_worst_ask(self):
        return self.asks.max_price()

    def tape_dump(self, filename, filemode, tapemode):
        dumpfile = open(filename, filemode)
        for tapeitem in self.tape:
            dumpfile.write('Time: %s, Price: %s, size: %s\n' % (tapeitem['time'],
                                                                    tapeitem['price'],
                                                                    tapeitem['size']))
        dumpfile.close()
        if tapemode == 'wipe':
            self.tape = []

    def __str__(self):
        tempfile = StringIO()
        tempfile.write("***Bids***\n")
        if self.bids != None and len(self.bids) > 0:
            for key, value in self.bids.price_tree.items(reverse=True):
                tempfile.write('%s' % value)
        tempfile.write("\n***Asks***\n")
        if self.asks != None and len(self.bids) > 0:
            for key, value in self.asks.price_tree.items():
                tempfile.write('%s' % value)
        tempfile.write("\n***Trades***\n")
        if self.tape != None and len(self.tape) > 0:
            num = 0
            for entry in self.tape:
                if num < 5: # get last 5 entries
                    tempfile.write(str(entry['size']) + " @ " + str(entry['price']) + " (" + str(entry['timestamp']) + ")\n")
                    num += 1
                else:
                    break
        tempfile.write("\n")
        return tempfile.getvalue()

