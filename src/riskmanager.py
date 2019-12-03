import time

class RiskManager:
    def __init__(self, global_risk, strategy_risk):
        self.global_risk = global_risk
        self.strategy_risk = strategy_risk

    def receive_order(self):
        


class Comms:
    def __init__(self, comms_config):
        self.comms_config = comms_config

    def get_current_comm(self):
        return 0

class OrderManager:
    def __init__(self, life_time=10):
        self.order_life_time = 10
        self.outstaning_orders= {}

    def receive_order(self, orders):
        """check the received order if last fills more than life time cancel it
        """
        for order in orders:
            if order["id"] not in self.outstaning_orders:
                self.outstaning_orders[order["id"]] = time.time()
            else:
                if time.time() - self.outstaning_orders[order["id"]] > self.order_life_time:
                    self.terminal_order(self.outstaning_orders[order["id"]])

    def receive_fill(self, fill):
        pass

    def check_outstanding_order(self):
        pass

    def terminal_order(self, order_id):
        pass
