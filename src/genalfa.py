import time 
from collections import OrderedDict, defaultdict
from decimal import Decimal
from utils import ORDER_TYPE, Mode
from lightmatchingengine.lightmatchingengine import Side

class Btrade:
    def __init__(self, init_price, mode=Mode.TEST, start_pos=5, risk_limit=5000000, outstanding_limit=20):
        self.mode = mode
        self.record_manager = defaultdict()
        self.positions = []
        self.risk_limit = risk_limit
        self.outstanding_limit = outstanding_limit
        self.pending_orders = defaultdict(list)
        self.price_stock = defaultdict(OrderedDict)
        self.current_pnl = Decimal()
        self.current_pos_lst = [[start_pos, init_price]]
        self.volume = Decimal(0.5)
        self.target_buy_price = []
        self.target_sell_price = []
        self.start_pos = init_price * start_pos
        self.cost_basis = init_price
        

    def data_reveiver(self, data):
        raise NotImplementedError()

    def get_singal(self):
        raise NotImplementedError()

    def no_data_reveived(self):
        return self.target_buy_price and self.target_sell_price

    def is_valid_order(self, side="buy"):
        if self.get_current_risk() > self.risk_limit:
            return False
        if side == "sell" and (self.get_current_position() - self.volume) < 0:
            return False

        return True

    def remove_all_outstadning_order(self):
        remove_list = [trade_id for trade_id in self.record_manager]
        self.pending_orders[ORDER_TYPE.CANCEL].extend(remove_list) 

        self.record_manager = defaultdict()
        print("remove all orders")


    def remove_long_standing_order(self):
        remove_list = []
        for trade_id, info in self.record_manager.items():
            _, create_time, _ , _ = info
             
            if time.time() - create_time > self.outstanding_limit:
                self.pending_orders[ORDER_TYPE.CANCEL].append(trade_id)
                remove_list.append(trade_id)

        for trade_id in remove_list:
            del self.record_manager[trade_id]
            print(f"remove order {trade_id}")
        
    def get_cost_basis(self, cost, qty):
        cur_qty = self.get_current_position()
        self.cost_basis = (self.cost_basis * cur_qty + cost * qty) / (cur_qty + qty)

    def receive_fill(self, fill):
        left_size, create_time, cost, side = self.record_manager[fill.trade_id] 
        if left_size > fill.trade_qty:
            left_size -= fill.trade_qty
            qty = fill.trade_qty
        else:
            qty = left_size
            left_size = 0

        new_pos = {"qty": str(qty), "origin_time": create_time,
                    "cost": str(cost), "origin_side": side,
                    "realized_pnl": str(self.get_current_pnl()),
                    "current_pos": str(self.get_current_position())}

        signed_qty = (Decimal(1) if side == Side.BUY else Decimal(-1)) * qty

        if side == Side.SELL:
            self.current_pnl += qty * (fill.trade_price - self.cost_basis)
        else:
            self.get_cost_basis(cost, signed_qty)
        self.current_pos_lst.append([signed_qty, cost])

        self.positions.append(new_pos)
        if left_size > Decimal(0):
            self.record_manager[fill.trade_id] = (left_size, create_time, cost, side)
        else:
            del self.record_manager[fill.trade_id]

    def get_current_pnl(self):
        return self.current_pnl

    def get_current_unr_pnl(self, top_bid, top_ask):
        res = Decimal() 
        for qty, cost in self.current_pos_lst:
            if qty > 0:
                res += (top_ask - cost) * qty
            elif qty < 0: 
                res += (cost - top_bid) * abs(qty)

        return res

    def get_current_position(self):
        return sum(qty for qty, _ in self.current_pos_lst)


    def get_current_risk(self):
        res = Decimal() 
        for _, info in self.record_manager.items():
            left_size, _, cost, _ = info
            res += cost * left_size

        return res

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
        self.record_manager[order_id] = (order.qty, time.time(), order.price, order.side)
        self.price_stock[order.price][order_id] = order.qty

        for trade in trades:
            if trade.order_id != order_id:
                self.receive_fill(trade)
            
        return self.positions


class Naive1(Btrade):
    name = "naive2"

    def __init__(self, *args, **kwargs):
        self.target_buy_price = []
        self.target_sell_price = []
        self.volume = 0.4
        self.order_id = int(time.time()*1000)
        self.data_needs = {"book"}
        self.waiting_time = 0.005
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

    def create_order(self):
       if self.new_trades:
            self.new_trades = False
            for price in self.target_buy_price:
                if not self.is_valid_order():
                    print("Risk limit reached")
                    continue
                self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume , 
                               "side": "buy", "type": "limit",
                               "client_oid": self.get_order_id(),
                               "instrument_id": ""})
            for price in self.target_sell_price:
                if not self.is_valid_order("sell"):
                    print("Risk limit reached")
                    continue 
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


class Naive2(Btrade):
    name = "naive_alpha04"

    def __init__(self, *args, **kwargs):
        self.target_buy_price = []
        self.target_sell_price = []
        self.weight = []
        self.volume = 0.2
        self.order_id = int(time.time()*1000)
        self.data_needs = {"book"}
        self.waiting_time = 0.1
        self.pre_timestampe = 0
        self.new_trades = False
        self.alpha = 1
        self.threshold = 0.2
        super(Naive2, self).__init__(*args, **kwargs)

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
            self.weight = [[Decimal(0.5), Decimal(1.5)], [Decimal(1.5), Decimal(0.5)]]
            self.pre_timestampe = timestamp
            self.new_trades = True

    def create_order(self):
       if self.new_trades:
            self.new_trades = False
            if self.alpha > self.threshold: # go down
                for (w, price) in zip(self.weight[1], self.target_buy_price):
                    if not self.is_valid_order():
                        print("Risk limit reached")
                        continue
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w ,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for (w, price) in zip(self.weight[1], self.target_sell_price):
                    if not self.is_valid_order("sell"):
                        print("Risk limit reached")
                        continue
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                    "side": "sell", "type": "limit",
                                    "client_oid": self.get_order_id(),
                                    "instrument_id": ""})
            elif self.alpha < - self.threshold:
                for (w, price) in zip(self.weight[1], self.target_buy_price):
                    if not self.is_valid_order():
                        print("Risk limit reached")
                        continue
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for (w, price) in zip(self.weight[1], self.target_sell_price):
                    if not self.is_valid_order("sell"):
                        print("Risk limit reached")
                        continue
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume * w,
                                    "side": "sell", "type": "limit",
                                    "client_oid": self.get_order_id(),
                                    "instrument_id": ""})
            else:
                for price in self.target_buy_price:
                    if not self.is_valid_order():
                        print("Risk limit reached")
                        continue
                    self.pending_orders[ORDER_TYPE.ORDER].append({"price": price, "size": self.volume ,
                                   "side": "buy", "type": "limit",
                                   "client_oid": self.get_order_id(),
                                   "instrument_id": ""})
                for price in self.target_sell_price:
                    if not self.is_valid_order("sell"):
                        print("Risk limit reached")
                        continue
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
