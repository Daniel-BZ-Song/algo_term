from queue import Queue
import time 
from collections import OrderedDict, defaultdict
from decimal import Decimal
from utils import ORDER_TYPE, Mode, RECEIVE_TYPE
class Btrade:
    def __init__(self, mode=Mode.TEST, risk_limit=50, outstanding_limit=180):
        self.mode = mode
        self.record_manager = defaultdict()
        self.positions = []
        self.risk_limit = risk_limit
        self.outstanding_limit = outstanding_limit
        self.pending_orders = defaultdict(list)
        self.price_stock = defaultdict(OrderedDict)
        

    def data_reveiver(self, data):
        raise NotImplementedError()

    def get_singal(self):
        raise NotImplementedError()

    def is_valid_order(self, price):
        if self.get_current_risk() > self.risk_limit:
            return False

        return True

    def remove_long_standing_order(self):
        remove_list = []
        for trade_id, info in self.record_manager.items():
            _, create_time, _ = info
             
            if time.time() - create_time > self.outstanding_limit:
                self.pending_orders[ORDER_TYPE.CANCEL].append(trade_id)
                remove_list.append(trade_id)

        for trade_id in remove_list:
            del self.record_manager[trade_id]
            print(f"remove order {trade_id}")
                

    def receive_fill(self, fill):
        print(self.price_stock[fill.trade_price])
        left_size, create_time, cost = self.record_manager[fill.trade_id] 
        if left_size > fill.trade_qty:
            left_size -= fill.trade_qty
            qty = fill.trade_qty
        else:
            qty = left_size
            left_size = 0

        pnl = str((fill.trade_price-cost) * qty)
        new_pos = {"price": str(fill.trade_price), "qty": str(qty), 
                    "side": fill.trade_side, "origin_time": create_time,
                    "cost": str(cost),  "pnl": pnl}
        self.positions.append(new_pos)
        if left_size > Decimal(0):
            self.record_manager[fill.trade_id] = (left_size, create_time, cost)
        else:
            del self.record_manager[fill.trade_id]

    def get_current_risk(self):
        res = Decimal() 
        for _, info in self.record_manager.items():
            left_size, _, cost = info
            res += cost * left_size

        return res

class Naive1(Btrade):
    name = "naive3"

    def __init__(self, *args, **kwargs):
        self.target_buy_price = []
        self.target_sell_price = []
        self.volume = 0.5
        self.order_id = int(time.time()*1000)
        self.data_needs = {"book"}
        self.waiting_time = 2
        self.pre_timestampe = 0
        self.new_trades = False
        super(Naive1, self).__init__(*args, **kwargs)

    def get_order_id(self):
        self.order_id += 1
        return self.order_id 

    def data_reveiver(self, book, timestamp):
        if timestamp - self.pre_timestampe >= self.waiting_time:
            asks = [p for p in book.asks][:2]
            bids = [p for p in book.bids][:2]

            self.target_buy_price = [bids[0], bids[1]]
            self.target_sell_price = [asks[0], asks[1]]
            self.pre_timestampe = timestamp
            self.new_trades = True

    def no_data_reveived(self):
        return self.target_buy_price and self.target_sell_price

    def create_order(self):
       if self.new_trades:
            self.new_trades = False
            for price in self.target_buy_price:
                self.is_valid_order(price)
                self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume , 
                               "side": "buy", "type": "limit",
                               "client_oid": self.get_order_id(),
                               "instrument_id": ""})
            for price in self.target_sell_price:
                self.is_valid_order(price)
                self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume , 
                                "side": "sell", "type": "limit",
                                "client_oid": self.get_order_id(),
                                "instrument_id": ""})
            self.target_buy_price = []
            self.target_sell_price = []

    def creat_requet(self):
        self.pending_orders[ORDER_TYPE.ORDER] = []
        self.remove_long_standing_order()
        self.create_order()

        return self.pending_orders

    def process_market_trade(self, trades):
        self.positions = [] 
        for trade in trades:
            if trade.trade_id in self.record_manager:
                self.receive_fill(trade)
        
        return self.positions

    def process(self, order, trades):
        if order is None:
            return {} #cross book

        self.positions = []
        order_id = order.order_id
        self.record_manager[order_id] = (order.qty, time.time(), order.price)
        self.price_stock[order.price][order_id] = order.qty

        for trade in trades:
            if trade.order_id != order_id:
                self.receive_fill(trade)
            
        return self.positions
    
    
    
    class Naive2(Btrade):
    name = "naive_alpha01"

    def __init__(self, *args, **kwargs):
        self.target_buy_price = []
        self.target_sell_price = []
        self.weight = []
        self.volume = 0.5
        self.order_id = int(time.time()*1000)
        self.data_needs = {"book"}
        self.waiting_time = 2
        self.pre_timestampe = 0
        self.new_trades = False
        self.alpha = 1
        self.threshold = 0.2
        super(Naive1, self).__init__(*args, **kwargs)

    def get_order_id(self):
        self.order_id += 1
        return self.order_id 

    def data_reveiver(self, book, timestamp):
        if timestamp - self.pre_timestampe >= self.waiting_time:
            asks = [p for p in book.asks][:5]
            bids = [p for p in book.bids][:5]
            ask_volume = [sum(o.qty for o in book.asks[ap]) for ap in asks]
            bid_volume = [sum(o.qty for o in book.bids[bp]) for bp in bids]

            # alpha > 0, ask side thicker, price goes down, buy order sell
            self.alpha = sum(ask_volume[:3])/sum(bid_volume[:3]) - 1

            self.target_buy_price = [bids[0], bids[1], bids[2]]
            self.target_sell_price = [asks[0], asks[1], asks[2]]
            self.weight = [[0.5, 1.5], [1.5, 0.5]]
            self.pre_timestampe = timestamp
            self.new_trades = True

    def no_data_reveived(self):
        return self.target_buy_price and self.target_sell_price

    def create_order(self):
       if self.new_trades:
            self.new_trades = False
            if self.alpha > self.threshold: # go down
                for (w, price) in zip(self.weight[0], self.target_buy_price):
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w ,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for (w, price) in zip(self.weight[1], self.target_sell_price):
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                    "side": "sell", "type": "limit",
                                    "client_oid": self.get_order_id(),
                                    "instrument_id": ""})
            elif self.alpha < - self.threshold:
                for (w, price) in zip(self.weight[1], self.target_buy_price):
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for (w, price) in zip(self.weight[1], self.target_sell_price):
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                    "side": "sell", "type": "limit",
                                    "client_oid": self.get_order_id(),
                                    "instrument_id": ""})
            else:
                for price in self.target_buy_price:
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume ,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for price in self.target_sell_price:
                    self.is_valid_order(price)
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume ,
                                    "side": "sell", "type": "limit",
                                    "client_oid": self.get_order_id(),
                                    "instrument_id": ""})

            self.target_buy_price = []
            self.target_sell_price = []

    def creat_requet(self):
        self.pending_orders[ORDER_TYPE.ORDER] = []
        self.remove_long_standing_order()
        self.create_order()

        return self.pending_orders

    def process_market_trade(self, trades):
        self.positions = [] 
        for trade in trades:
            if trade.trade_id in self.record_manager:
                self.receive_fill(trade)
        
        return self.positions

    def process(self, order, trades):
        if order is None:
            return {} #cross book

        self.positions = []
        order_id = order.order_id
        self.record_manager[order_id] = (order.qty, time.time(), order.price)
        self.price_stock[order.price][order_id] = order.qty

        for trade in trades:
            if trade.order_id != order_id:
                self.receive_fill(trade)
            
        return self.positions
