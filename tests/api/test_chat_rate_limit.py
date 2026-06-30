import os
import sys
import time
import asyncio
from pathlib import Path
import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from backend.app.deps import limit_chat_rate

class MockRedisPipeline:
    def __init__(self, card_values):
        self.card_values = card_values
        self.call_idx = 0
        self.expired = False
        self.added = {}
        self.keys = []

    def zremrangebyscore(self, key, min_val, max_val):
        self.keys.append(key)
        return self

    def zadd(self, key, mapping):
        self.keys.append(key)
        self.added.update(mapping)
        return self

    def zcard(self, key):
        self.keys.append(key)
        return self

    def expire(self, key, seconds):
        self.keys.append(key)
        self.expired = True
        return self

    def execute(self):
        val = self.card_values[self.call_idx]
        self.call_idx += 1
        return [0, 1, val, True]


class MockRedisClient:
    def __init__(self, card_values):
        self.card_values = card_values
        self.pipeline_instance = MockRedisPipeline(card_values)
        self.removed_member = None

    def pipeline(self):
        return self.pipeline_instance

    def zrem(self, key, member):
        self.removed_member = member
        return 1


class MockClientHost:
    def __init__(self, host):
        self.host = host


class MockRequest:
    def __init__(self, headers, host=None):
        self.headers = headers
        self.client = MockClientHost(host) if host else None


def test_limit_chat_rate_success():
    # Card values for 10 requests: 1, 2, ..., 10
    card_values = list(range(1, 11))
    redis_client = MockRedisClient(card_values)
    request = MockRequest(headers={}, host="192.168.1.1")
    
    # All 10 requests should pass without raising
    for _ in range(10):
        res = asyncio.run(limit_chat_rate(request, redis_client))
        assert res is None


def test_limit_chat_rate_exceeded():
    # 11th request returns card value 11 (exceeds limit 10)
    redis_client = MockRedisClient([11])
    request = MockRequest(headers={}, host="192.168.1.1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(limit_chat_rate(request, redis_client))
        
    assert exc_info.value.status_code == 429
    assert "Bạn đã vượt quá giới hạn gửi 10 tin nhắn trong 10 phút" in exc_info.value.detail
    # Verify that the member was removed from Redis
    assert redis_client.removed_member is not None


def test_limit_chat_rate_extracts_ip_from_x_forwarded_for():
    redis_client = MockRedisClient([1])
    request = MockRequest(headers={"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}, host="127.0.0.1")
    
    asyncio.run(limit_chat_rate(request, redis_client))
    
    # Verify the key added to zadd contains the correct IP
    assert any("rate_limit:chat:ip:203.0.113.195" in k for k in redis_client.pipeline_instance.keys)


def test_limit_chat_rate_extracts_ip_from_x_real_ip():
    redis_client = MockRedisClient([1])
    request = MockRequest(headers={"x-real-ip": "198.51.100.1"}, host="127.0.0.1")
    
    asyncio.run(limit_chat_rate(request, redis_client))
    
    assert any("rate_limit:chat:ip:198.51.100.1" in k for k in redis_client.pipeline_instance.keys)
