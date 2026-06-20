import sys
sys.path.insert(0, r'C:\Users\yoge1426\Downloads\llm-chatbot\microservices\auth-service')
import main
from fastapi.testclient import TestClient

class FakeRedis:
    def __init__(self):
        self.data = {}

    def ping(self):
        return True

    def exists(self, key):
        return key in self.data

    def hset(self, key, mapping=None):
        self.data[key] = {k: str(v) for k, v in mapping.items()}

    def hgetall(self, key):
        return self.data.get(key, {})

    def sadd(self, key, *values):
        current = self.data.get(key, set())
        if not isinstance(current, set):
            current = set(current)
        current.update(values)
        self.data[key] = current

    def smembers(self, key):
        return self.data.get(key, set())

    def expire(self, key, seconds):
        pass

    def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)

fake = FakeRedis()
main.redis_client = fake
client = TestClient(main.app)
resp = client.post('/api/login', json={'username': 'admin', 'password': 'admin123'})
print(resp.status_code)
print(resp.text)
print(fake.data)
