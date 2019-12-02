class Execution:
    def __init__(self, config):
        self.config = config

    def receive(self, receive_channel, session):
        for order in receive_channel:
            session. 