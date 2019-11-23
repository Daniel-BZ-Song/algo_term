
from flask import Flask, escape, request

app = Flask(__name__)

class TickData:
    def __init__(self):
        pass

@app.route('/')
def hello():
    name = request.args.get("name", "World")
    return f'Hello, {escape(name)}!'