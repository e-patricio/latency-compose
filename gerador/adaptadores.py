import base64
import requests
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement
from cassandra.policies import WhiteListRoundRobinPolicy

ENDPOINTS_ETCD = [
    "http://172.21.0.11:2379",
    "http://172.21.0.12:2379",
    "http://172.21.0.13:2379",
]

ENDPOINTS_CASSANDRA = [
    "172.21.0.11",
    "172.21.0.12",
    "172.21.0.13",
]


class EtcdAdapter:
    def __init__(self, endpoints=None, timeout=2.0, serializable=False):
        self.endpoints = endpoints or list(ENDPOINTS_ETCD)
        self.timeout = timeout
        self.serializable = serializable
        self.session = requests.Session()
        self.idx = 0

    def _next_base(self):
        ep = self.endpoints[self.idx % len(self.endpoints)]
        self.idx += 1
        return f"{ep}/v3/kv"

    def put(self, key: str, value: bytes):
        payload = {
            "key": base64.b64encode(key.encode("utf-8")).decode("ascii"),
            "value": base64.b64encode(value).decode("ascii"),
        }
        last_err = None
        for _ in range(len(self.endpoints)):
            base = self._next_base()
            try:
                r = self.session.post(f"{base}/put", json=payload, timeout=self.timeout)
                r.raise_for_status()
                return True
            except Exception as e:
                last_err = e
        raise last_err

    def get(self, key: str):
        payload = {
            "key": base64.b64encode(key.encode("utf-8")).decode("ascii"),
        }
        if self.serializable:
            payload["serializable"] = True

        last_err = None
        for _ in range(len(self.endpoints)):
            base = self._next_base()
            try:
                r = self.session.post(f"{base}/range", json=payload, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                kvs = data.get("kvs", [])
                if not kvs:
                    return None
                return base64.b64decode(kvs[0]["value"])
            except Exception as e:
                last_err = e
        raise last_err


cclass CassandraAdapter:
    def __init__(self, hosts=None, timeout=2.0, consistency=ConsistencyLevel.ONE):
        target_hosts = hosts or list(ENDPOINTS_CASSANDRA)
        policy = WhiteListRoundRobinPolicy(target_hosts)
        self.cluster = Cluster(
            contact_points=target_hosts,
            load_balancing_policy=policy,
            connect_timeout=max(timeout, 10.0),
        )
        self.session = self.cluster.connect("lab")
        self.session.default_timeout = timeout
        self.consistency = consistency

        self.stmt_put = self.session.prepare("INSERT INTO kv (k, v) VALUES (?, ?)")
        self.stmt_put.consistency_level = self.consistency

        self.stmt_get = self.session.prepare("SELECT v FROM kv WHERE k = ?")
        self.stmt_get.consistency_level = self.consistency

    def put(self, key: str, value: bytes):
        self.session.execute(self.stmt_put, (key, value), timeout=self.session.default_timeout)
        return True

    def get(self, key: str):
        row = self.session.execute(self.stmt_get, (key,), timeout=self.session.default_timeout).one()
        return row.v if row else None

    def close(self):
        self.cluster.shutdown()