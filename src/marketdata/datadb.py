from pymongo import MongoClient

class DataDB:
    def __init__(self, db_name, port=27017):
        self.db_name = db_name
        self.port = port 
        self.collections = {}

    def start_client(self):
        client = MongoClient()
        client = MongoClient('localhost', self.port)
        if self.db_name not in client.list_database_names():
            print("Wrong db")
        db_obj = client[self.db_name]
        self.collections = {collection_name: db_obj[collection_name] for collection_name in db_obj.list_collection_names ()}

    def write_data(self, table_name, data):
        poster = self.collections[table_name].posts
        if isinstance(data, dict):
            poster.insert_one(data)
        elif isinstance(data, list):
            if data:
                poster.insert_many(data)

    def get_data(self, table_name):
        poster = self.collections[table_name].posts
        for data in poster.find({}, {'_id': False}):
            yield data
            