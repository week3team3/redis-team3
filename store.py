class Store:
    def __init__(self):
        self.data = {}

    def set(self, key, value):
        self.data[key] = value
        return 'OK'
    
    def get(self, key):
        return self.data.get(key, '(nil)')
    
    def delete(self, key):
        db = self.data
        val = db.pop(key, '0')
        return val
    
    def increment(self, key):
        db = self.data
        val = int(db[key])
        val += 1
        db[key] = val
        return str(val)

