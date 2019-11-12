import threading
import time
import random
import queue

q = queue.Queue()

class data(threading.Thread):
    def __init__(self):
        super(data,self).__init__()
        
    def run(self):
        for i in range(10):
            if not q.full():
                q.put(i)
                time.sleep(random.random())
        return

class alfa(threading.Thread):
    def __init__(self):
        super(alfa,self).__init__()
        return

    def run(self):
        while True:
            if not q.empty():
                item = q.get()
                print('I receive: ', item)
                time.sleep(random.random())
        return

if __name__ == '__main__':
    
    p = data()
    c = alfa()

    p.start()
    time.sleep(2)
    c.start()
    time.sleep(2)
