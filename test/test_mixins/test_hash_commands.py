import pytest
import redis
import redis.client

from test.testtools import key_val_dict


# Tests for the hash type.

def test_hstrlen_missing(r):
    assert r.hstrlen('foo', 'doesnotexist') == 0

    r.hset('foo', 'key', 'value')
    assert r.hstrlen('foo', 'doesnotexist') == 0


def test_hstrlen(r):
    r.hset('foo', 'key', 'value')
    assert r.hstrlen('foo', 'key') == 5


def test_hset_then_hget(r):
    assert r.hset('foo', 'key', 'value') == 1
    assert r.hget('foo', 'key') == b'value'


def test_hset_update(r):
    assert r.hset('foo', 'key', 'value') == 1
    assert r.hset('foo', 'key', 'value') == 0


def test_hset_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hset('foo', 'key', 'value')


def test_hgetall(r):
    assert r.hset('foo', 'k1', 'v1') == 1
    assert r.hset('foo', 'k2', 'v2') == 1
    assert r.hset('foo', 'k3', 'v3') == 1
    assert r.hgetall('foo') == {
        b'k1': b'v1',
        b'k2': b'v2',
        b'k3': b'v3'
    }


def test_hgetall_empty_key(r):
    assert r.hgetall('foo') == {}


def test_hgetall_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hgetall('foo')


def test_hexists(r):
    r.hset('foo', 'bar', 'v1')
    assert r.hexists('foo', 'bar') == 1
    assert r.hexists('foo', 'baz') == 0
    assert r.hexists('bar', 'bar') == 0


def test_hexists_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hexists('foo', 'key')


def test_hkeys(r):
    r.hset('foo', 'k1', 'v1')
    r.hset('foo', 'k2', 'v2')
    assert set(r.hkeys('foo')) == {b'k1', b'k2'}
    assert set(r.hkeys('bar')) == set()


def test_hkeys_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hkeys('foo')


def test_hlen(r):
    r.hset('foo', 'k1', 'v1')
    r.hset('foo', 'k2', 'v2')
    assert r.hlen('foo') == 2


def test_hlen_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hlen('foo')


def test_hvals(r):
    r.hset('foo', 'k1', 'v1')
    r.hset('foo', 'k2', 'v2')
    assert set(r.hvals('foo')) == {b'v1', b'v2'}
    assert set(r.hvals('bar')) == set()


def test_hvals_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hvals('foo')


def test_hmget(r):
    r.hset('foo', 'k1', 'v1')
    r.hset('foo', 'k2', 'v2')
    r.hset('foo', 'k3', 'v3')
    # Normal case.
    assert r.hmget('foo', ['k1', 'k3']) == [b'v1', b'v3']
    assert r.hmget('foo', 'k1', 'k3') == [b'v1', b'v3']
    # Key does not exist.
    assert r.hmget('bar', ['k1', 'k3']) == [None, None]
    assert r.hmget('bar', 'k1', 'k3') == [None, None]
    # Some keys in the hash do not exist.
    assert r.hmget('foo', ['k1', 'k500']) == [b'v1', None]
    assert r.hmget('foo', 'k1', 'k500') == [b'v1', None]


def test_hmget_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hmget('foo', 'key1', 'key2')


def test_hdel(r):
    r.hset('foo', 'k1', 'v1')
    r.hset('foo', 'k2', 'v2')
    r.hset('foo', 'k3', 'v3')
    assert r.hget('foo', 'k1') == b'v1'
    assert r.hdel('foo', 'k1') == 1
    assert r.hget('foo', 'k1') is None
    assert r.hdel('foo', 'k1') == 0
    # Since redis>=2.7.6 returns number of deleted items.
    assert r.hdel('foo', 'k2', 'k3') == 2
    assert r.hget('foo', 'k2') is None
    assert r.hget('foo', 'k3') is None
    assert r.hdel('foo', 'k2', 'k3') == 0


def test_hdel_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hdel('foo', 'key')


def test_hincrby(r):
    r.hset('foo', 'counter', 0)
    assert r.hincrby('foo', 'counter') == 1
    assert r.hincrby('foo', 'counter') == 2
    assert r.hincrby('foo', 'counter') == 3


def test_hincrby_with_no_starting_value(r):
    assert r.hincrby('foo', 'counter') == 1
    assert r.hincrby('foo', 'counter') == 2
    assert r.hincrby('foo', 'counter') == 3


def test_hincrby_with_range_param(r):
    assert r.hincrby('foo', 'counter', 2) == 2
    assert r.hincrby('foo', 'counter', 2) == 4
    assert r.hincrby('foo', 'counter', 2) == 6


def test_hincrby_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hincrby('foo', 'key', 2)


def test_hincrbyfloat(r):
    r.hset('foo', 'counter', 0.0)
    assert r.hincrbyfloat('foo', 'counter') == 1.0
    assert r.hincrbyfloat('foo', 'counter') == 2.0
    assert r.hincrbyfloat('foo', 'counter') == 3.0


def test_hincrbyfloat_with_no_starting_value(r):
    assert r.hincrbyfloat('foo', 'counter') == 1.0
    assert r.hincrbyfloat('foo', 'counter') == 2.0
    assert r.hincrbyfloat('foo', 'counter') == 3.0


def test_hincrbyfloat_with_range_param(r):
    assert r.hincrbyfloat('foo', 'counter', 0.1) == pytest.approx(0.1)
    assert r.hincrbyfloat('foo', 'counter', 0.1) == pytest.approx(0.2)
    assert r.hincrbyfloat('foo', 'counter', 0.1) == pytest.approx(0.3)


def test_hincrbyfloat_on_non_float_value_raises_error(r):
    r.hset('foo', 'counter', 'cat')
    with pytest.raises(redis.ResponseError):
        r.hincrbyfloat('foo', 'counter')


def test_hincrbyfloat_with_non_float_amount_raises_error(r):
    with pytest.raises(redis.ResponseError):
        r.hincrbyfloat('foo', 'counter', 'cat')


def test_hincrbyfloat_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hincrbyfloat('foo', 'key', 0.1)


def test_hincrbyfloat_precision(r):
    x = 1.23456789123456789
    assert r.hincrbyfloat('foo', 'bar', x) == x
    assert float(r.hget('foo', 'bar')) == x


def test_hsetnx(r):
    assert r.hsetnx('foo', 'newkey', 'v1') == 1
    assert r.hsetnx('foo', 'newkey', 'v1') == 0
    assert r.hget('foo', 'newkey') == b'v1'


def test_hmset_empty_raises_error(r):
    with pytest.raises(redis.DataError):
        r.hmset('foo', {})


def test_hmset(r):
    r.hset('foo', 'k1', 'v1')
    assert r.hmset('foo', {'k2': 'v2', 'k3': 'v3'}) is True


def test_hmset_wrong_type(r):
    r.zadd('foo', {'bar': 1})
    with pytest.raises(redis.ResponseError):
        r.hmset('foo', {'key': 'value'})


def test_empty_hash(r):
    r.hset('foo', 'bar', 'baz')
    r.hdel('foo', 'bar')
    assert not r.exists('foo')


def test_hset_removing_last_field_delete_key(r):
    r.hset(b'3L', b'f1', b'v1')
    r.hdel(b'3L', b'f1')
    assert r.keys('*') == []


def test_hscan(r):
    # Set up the data
    name = 'hscan-test'
    for ix in range(20):
        k = 'key:%s' % ix
        v = 'result:%s' % ix
        r.hset(name, k, v)
    expected = r.hgetall(name)
    assert len(expected) == 20  # Ensure we know what we're testing

    # Test that we page through the results and get everything out
    results = {}
    cursor = '0'
    while cursor != 0:
        cursor, data = r.hscan(name, cursor, count=6)
        results.update(data)
    assert expected == results

    # Test the iterator version
    results = {}
    for key, val in r.hscan_iter(name, count=6):
        results[key] = val
    assert expected == results

    # Now test that the MATCH functionality works
    results = {}
    cursor = '0'
    while cursor != 0:
        cursor, data = r.hscan(name, cursor, match='*7', count=100)
        results.update(data)
    assert b'key:7' in results
    assert b'key:17' in results
    assert len(results) == 2

    # Test the match on iterator
    results = {}
    for key, val in r.hscan_iter(name, match='*7'):
        results[key] = val
    assert b'key:7' in results
    assert b'key:17' in results
    assert len(results) == 2


def test_hscan_delete_key_while_scanning_should_not_returns_it_in_scan(r):
    size = 600
    name = 'hscan-test'
    all_keys_dict = key_val_dict(size=size)
    r.hset(name, mapping=all_keys_dict)
    assert len(r.hgetall(name)) == size

    cursor, keys = r.hscan(name, 0)
    assert len(keys) < len(all_keys_dict)

    key_to_remove = next(x for x in all_keys_dict if x not in keys)
    assert r.hdel(name, key_to_remove) == 1
    assert r.hget(name, key_to_remove) is None
    while cursor != 0:
        cursor, data = r.hscan(name, cursor=cursor)
        keys.update(data)
    assert len(set(keys)) == len(keys)
    assert len(keys) == size - 1
    assert key_to_remove not in keys
