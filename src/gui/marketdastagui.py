import json
from flask import Flask, render_template, jsonify, Response, redirect, request, url_for
import pandas as pd
from pymongo import MongoClient
import itertools
import time

app = Flask(__name__, template_folder="template")

def get_data():
    client = MongoClient()
    client = MongoClient('localhost', 27017)
    db_obj = client["market_data"]

    return db_obj["trades.posts"].find()


@app.route('/')
def index():
    data_gen = get_data()
    if request.headers.get('accept') == 'text/event-stream':
        def events():
            for icon in itertools.cycle(r'\|/-'):
                trade = next(data_gen)
                yield "data: %sIncoming trade: %s %s %s\n\n" % (icon, trade['price'], trade['size'], trade["side"])
                yield "chart_data: %s" % trade['price']
                time.sleep(0.2)  # an artificial delay
        return Response(events(), content_type='text/event-stream')
    return redirect(url_for('static', filename='index.html'))

@app.rounte("/data")
def test():
    
    render_template('template.html', my_string="Wheeeee!", my_list=[0,1,2,3,4,5])

if __name__ == "__main__":
    app.run(debug=True)