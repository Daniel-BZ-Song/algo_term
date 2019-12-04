from pymongo import MongoClient, ASCENDING

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
        self.db_obj = client[self.db_name]
        self.collections = {collection_name: self.db_obj[collection_name] for collection_name in self.db_obj.list_collection_names ()}

    def write_data(self, table_name, data):
        if table_name not in self.collections:
            self.collections[table_name] = self.db_obj[table_name]
        poster = self.collections[table_name].posts
        if isinstance(data, dict):
            poster.insert_one(data)
        elif isinstance(data, list):
            if data:
                poster.insert_many(data)

    def regex_find(self, condition, table_name):
        poster = self.collections[table_name]
        return poster.find_one(condition)

    def get_first_data(self, table_name):
        poster = self.collections[table_name]
        return poster.find_one()

    def get_data(self, table_name):
        poster = self.collections[table_name].posts
        for data in poster.find().sort('timestamp', ASCENDING):
            yield data
            