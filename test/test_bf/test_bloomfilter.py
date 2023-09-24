import pytest
import redis


def test_bf_add(r: redis.Redis):
    assert r.bf().add('key', 'value') == 1
    assert r.bf().add('key', 'value') == 0

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().add('key1', 'v')