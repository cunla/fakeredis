import time

import pytest
import redis

from fakeredis import _msgs as msgs
from fakeredis._stream import XStream
from test import testtools


def get_ids(results):
    return [result[0] for result in results]


def add_items(r: redis.Redis, stream: str, n: int):
    id_list = list()
    for i in range(n):
        id_list.append(r.xadd(stream, {"k": i}))
    return id_list


def test_xstream(r: redis.Redis):
    stream = XStream()
    stream.add([0, 0, 1, 1, 2, 2, 3, 3], '0-1')
    stream.add([1, 1, 2, 2, 3, 3, 4, 4], '1-2')
    stream.add([2, 2, 3, 3, 4, 4], '1-3')
    stream.add([3, 3, 4, 4], '2-1')
    stream.add([3, 3, 4, 4], '2-2')
    stream.add([3, 3, 4, 4], '3-1')
    assert len(stream) == 6
    i = iter(stream)
    assert next(i) == [b'0-1', [0, 0, 1, 1, 2, 2, 3, 3]]
    assert next(i) == [b'1-2', [1, 1, 2, 2, 3, 3, 4, 4]]
    assert next(i) == [b'1-3', [2, 2, 3, 3, 4, 4]]
    assert next(i) == [b'2-1', [3, 3, 4, 4]]
    assert next(i) == [b'2-2', [3, 3, 4, 4]]

    assert stream.find_index('1-2') == (1, True)
    assert stream.find_index('0-1') == (0, True)
    assert stream.find_index('2-1') == (3, True)
    assert stream.find_index('1-4') == (3, False)

    lst = stream.irange((0, 2), (3, 0))
    assert len(lst) == 4

    stream = XStream()
    assert stream.delete(['1']) == 0
    id_str = stream.add([0, 0, 1, 1, 2, 2, 3, 3])
    assert stream.delete([id_str, ]) == 1
    assert len(stream) == 0


@pytest.mark.max_server('6.3')
def test_xadd_redis6(r: redis.Redis):
    stream = "stream"
    before = time.time()
    m1 = r.xadd(stream, {"some": "other"})
    after = time.time()
    ts1, seq1 = m1.decode().split('-')
    seq1 = int(seq1)
    m2 = r.xadd(stream, {'add': 'more'}, id=f'{ts1}-{seq1 + 1}')
    ts2, seq2 = m2.decode().split('-')
    assert int(1000 * before) <= int(ts1) <= int(1000 * after)
    assert ts1 == ts2
    assert int(seq2) == int(seq1) + 1

    stream = "stream2"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    ts1 = int(ts1) - 1
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-1')


@pytest.mark.min_server('7')
def test_xadd_redis7(r: redis.Redis):
    stream = "stream"
    before = time.time()
    m1 = r.xadd(stream, {"some": "other"})
    after = time.time()
    ts1, seq1 = m1.decode().split('-')
    m2 = r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    ts2, seq2 = m2.decode().split('-')
    assert int(1000 * before) <= int(ts1) <= int(1000 * after)
    assert ts1 == ts2
    assert int(seq2) == int(seq1) + 1

    stream = "stream2"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    ts1 = int(ts1) - 1
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-1')


def test_xadd_maxlen(r: redis.Redis):
    stream = "stream"
    id_list = add_items(r, stream, 10)
    maxlen = 5
    id_list.append(r.xadd(stream, {'k': 'new'}, maxlen=maxlen, approximate=False))
    assert r.xlen(stream) == maxlen
    results = r.xrange(stream, id_list[0])
    assert get_ids(results) == id_list[len(id_list) - maxlen:]
    with pytest.raises(redis.ResponseError):
        testtools.raw_command(
            r, 'xadd', stream,
            'maxlen', '3', 'minid', 'sometestvalue', 'field', 'value')


def test_xadd_minid(r: redis.Redis):
    stream = "stream"
    id_list = add_items(r, stream, 10)
    minid = id_list[6]
    id_list.append(r.xadd(stream, {'k': 'new'}, minid=minid, approximate=False))
    assert r.xlen(stream) == len(id_list) - 6
    results = r.xrange(stream, id_list[0])
    assert get_ids(results) == id_list[6:]


def test_xtrim(r: redis.Redis):
    stream = "stream"

    # trimming an empty key doesn't do anything
    assert r.xtrim(stream, 1000) == 0
    add_items(r, stream, 4)

    # trimming an amount large than the number of messages
    # doesn't do anything
    assert r.xtrim(stream, 5, approximate=False) == 0

    # 1 message is trimmed
    assert r.xtrim(stream, 3, approximate=False) == 1


@pytest.mark.min_server("6.2.4")
def test_xtrim_minlen_and_length_args(r: redis.Redis):
    stream = "stream"
    add_items(r, stream, 4)

    # Future self: No limits without approximate, according to the api
    # with pytest.raises(redis.ResponseError):
    #     assert r.xtrim(stream, 3, approximate=False, limit=2)

    with pytest.raises(redis.DataError):
        assert r.xtrim(stream, maxlen=3, minid="sometestvalue")

    with pytest.raises(redis.ResponseError):
        testtools.raw_command(r, 'xtrim', stream, 'maxlen', '3', 'minid', 'sometestvalue')
    # minid with a limit
    stream = 's2'
    m1 = add_items(r, stream, 4)[0]
    assert r.xtrim(stream, minid=m1, limit=3) == 0

    # pure minid
    m4 = add_items(r, stream, 4)[-1]
    assert r.xtrim(stream, approximate=False, minid=m4) == 7

    # minid approximate
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    assert r.xtrim(stream, approximate=False, minid=m3) == 3


def test_xadd_nomkstream(r: redis.Redis):
    r.xadd('stream2', {"some": "other"}, nomkstream=True)
    assert r.xlen('stream2') == 0
    # nomkstream option
    stream = "stream"
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"some": "other"}, nomkstream=False)
    assert r.xlen(stream) == 2
    r.xadd(stream, {"some": "other"}, nomkstream=True)
    assert r.xlen(stream) == 3


def test_xrevrange(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    m4 = r.xadd(stream, {"foo": "bar"})

    results = r.xrevrange(stream, max=m4)
    assert get_ids(results) == [m4, m3, m2, m1]

    results = r.xrevrange(stream, max=m3, min=m2)
    assert get_ids(results) == [m3, m2]

    results = r.xrevrange(stream, min=m3)
    assert get_ids(results) == [m4, m3]

    results = r.xrevrange(stream, min=m2, count=1)
    assert get_ids(results) == [m4]


def test_xrange(r: redis.Redis):
    m = r.xadd('stream1', {"foo": "bar"})
    assert r.xrange('stream1') == [(m, {b"foo": b"bar"}), ]

    stream = 'stream2'
    m = testtools.raw_command(r, 'xadd', stream, '*', b'field', b'value', b'foo', b'bar')
    results = r.xrevrange(stream)

    assert results == [(m, {b'field': b'value', b'foo': b'bar'}), ]

    stream = "stream"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    m4 = r.xadd(stream, {"foo": "bar"})

    results = r.xrange(stream, min=m1)
    assert get_ids(results) == [m1, m2, m3, m4]

    results = r.xrange(stream, min=m2, max=m3)
    assert get_ids(results) == [m2, m3]

    results = r.xrange(stream, max=m3)
    assert get_ids(results) == [m1, m2, m3]

    results = r.xrange(stream, max=m2, count=1)
    assert get_ids(results) == [m1]


def get_stream_message(client, stream, message_id):
    """Fetch a stream message and format it as a (message_id, fields) pair"""
    response = client.xrange(stream, min=message_id, max=message_id)
    assert len(response) == 1
    return response[0]


def test_xread(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"bing": "baz"})

    expected = [
        [
            stream.encode(),
            [get_stream_message(r, stream, m1), get_stream_message(r, stream, m2)],
        ]
    ]
    # xread starting at 0 returns both messages
    assert r.xread(streams={stream: 0}) == expected

    expected = [[stream.encode(), [get_stream_message(r, stream, m1)]]]
    # xread starting at 0 and count=1 returns only the first message
    assert r.xread(streams={stream: 0}, count=1) == expected

    expected = [[stream.encode(), [get_stream_message(r, stream, m2)]]]
    # xread starting at m1 returns only the second message
    assert r.xread(streams={stream: m1}) == expected

    # xread starting at the last message returns an empty list
    assert r.xread(streams={stream: m2}) == []


def test_xread_bad_commands(r: redis.Redis):
    with pytest.raises(redis.ResponseError) as exc_info:
        testtools.raw_command(r, 'xread', 'foo', '11-1')
    print(exc_info)
    with pytest.raises(redis.ResponseError) as ex2:
        testtools.raw_command(r, 'xread', 'streams', 'foo', )
    print(ex2)


def test_xdel(r: redis.Redis):
    stream = "stream"

    # deleting from an empty stream doesn't do anything
    assert r.xdel(stream, 1) == 0

    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})

    # xdel returns the number of deleted elements
    assert r.xdel(stream, m1) == 1
    assert r.xdel(stream, m2, m3) == 2

    with pytest.raises(redis.ResponseError) as ex:
        testtools.raw_command(r, 'XDEL', stream)
    assert ex.value.args[0] == msgs.WRONG_ARGS_MSG6.format('xdel')[4:]
    assert r.xdel('non-existing-key', '1-1') == 0
