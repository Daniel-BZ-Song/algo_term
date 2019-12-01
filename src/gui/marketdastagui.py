import json
from flask import Flask, render_template
import pandas as pd
from pymongo import MongoClient


app = Flask(__name__)

def get_data():
    client = MongoClient()
    client = MongoClient('localhost', 27017)
    db_obj = client["market_data"]

    for record in db_obj["trades.posts"].find():
        yield record

@app.route("/")
def index():
    df = pd.read_csv('data').drop('Open', axis=1)
    chart_data = df.to_dict(orient='records')
    chart_data = json.dumps(chart_data, indent=2)
    data = {'chart_data': chart_data}
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)