## fakeredis: A python implementation of redis server

fakeredis is a pure-Python implementation of the redis-py python client
that simulates talking to a redis server. This was created for a single
purpose: **to write tests**. Setting up redis is not hard, but
many times you want to write tests that do not talk to an external server
(such as redis). This module now allows tests to simply use this
module as a reasonable substitute for redis.

For a list of supported/unsupported redis commands, see [Supported commands](./redis-commands/implemented_commands.md).

## Installation

To install fakeredis-py, simply:

```bash
pip install fakeredis        ## No additional modules support

pip install fakeredis[lua]   ## Support for LUA scripts

pip install fakeredis[json]  ## Support for RedisJSON commands
```

## How to Use

### General usage

FakeRedis can imitate Redis server version 6.x or 7.x.
If you do not specify the version, version 7 is used by default.

The intent is for fakeredis to act as though you're talking to a real
redis server. It does this by storing state internally.
For example:

```pycon
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis(version=6)
>>> r.set('foo', 'bar')
True
>>> r.get('foo')
'bar'
>>> r.lpush('bar', 1)
1
>>> r.lpush('bar', 2)
2
>>> r.lrange('bar', 0, -1)
[2, 1]
```

The state is stored in an instance of `FakeServer`. If one is not provided at
construction, a new instance is automatically created for you, but you can
explicitly create one to share state:

```pycon
>>> import fakeredis
>>> server = fakeredis.FakeServer()
>>> r1 = fakeredis.FakeStrictRedis(server=server)
>>> r1.set('foo', 'bar')
True
>>> r2 = fakeredis.FakeStrictRedis(server=server)
>>> r2.get('foo')
'bar'
>>> r2.set('bar', 'baz')
True
>>> r1.get('bar')
'baz'
>>> r2.get('bar')
'baz'
```

It is also possible to mock connection errors, so you can effectively test
your error handling. Simply set the connected attribute of the server to
`False` after initialization.

```pycon
>>> import fakeredis
>>> server = fakeredis.FakeServer()
>>> server.connected = False
>>> r = fakeredis.FakeStrictRedis(server=server)
>>> r.set('foo', 'bar')
ConnectionError: FakeRedis is emulating a connection error.
>>> server.connected = True
>>> r.set('foo', 'bar')
True
```

Fakeredis implements the same interface as `redis-py`, the popular
redis client for python, and models the responses of redis 6.x or 7.x.

### Use to test django cache

Update your cache settings:

```python
from fakeredis import FakeConnection

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': '...',
        'OPTIONS': {
            'connection_class': FakeConnection
        }
    }
}
```

You can use
django [`@override_settings` decorator](https://docs.djangoproject.com/en/4.1/topics/testing/tools/#django.test.override_settings)

### Use to test django-rq

There is a need to override `django_rq.queues.get_redis_connection` with
a method returning the same connection.

```python
from fakeredis import FakeRedisConnSingleton

django_rq.queues.get_redis_connection = FakeRedisConnSingleton()
```

## Known Limitations

Apart from unimplemented commands, there are a number of cases where fakeredis
won't give identical results to real redis. The following are differences that
are unlikely to ever be fixed; there are also differences that are fixable
(such as commands that do not support all features) which should be filed as
bugs in GitHub.

- Hyperloglogs are implemented using sets underneath. This means that the
  `type` command will return the wrong answer, you can't use `get` to retrieve
  the encoded value, and counts will be slightly different (they will in fact be
  exact).
- When a command has multiple error conditions, such as operating on a key of
  the wrong type and an integer argument is not well-formed, the choice of
  error to return may not match redis.

- The `incrbyfloat` and `hincrbyfloat` commands in redis use the C `long
  double` type, which typically has more precision than Python's `float`
  type.

- Redis makes guarantees about the order in which clients blocked on blocking
  commands are woken up. Fakeredis does not honour these guarantees.

- Where redis contains bugs, fakeredis generally does not try to provide exact
  bug-compatibility. It's not practical for fakeredis to try to match the set
  of bugs in your specific version of redis.

- There are a number of cases where the behaviour of redis is undefined, such
  as the order of elements returned by set and hash commands. Fakeredis will
  generally not produce the same results, and in Python versions before 3.6
  may produce different results each time the process is re-run.

- SCAN/ZSCAN/HSCAN/SSCAN will not necessarily iterate all items if items are
  deleted or renamed during iteration. They also won't necessarily iterate in
  the same chunk sizes or the same order as redis.

- DUMP/RESTORE will not return or expect data in the RDB format. Instead, the
  `pickle` module is used to mimic an opaque and non-standard format.
  **WARNING**: Do not use RESTORE with untrusted data, as a malicious pickle
  can execute arbitrary code.

## Local development environment

To ensure parity with the real redis, there are a set of integration tests
that mirror the unittests. For every unittest that is written, the same
test is run against a real redis instance using a real redis-py client
instance. In order to run these tests you must have a redis server running
on localhost, port 6379 (the default settings). **WARNING**: the tests will
completely wipe your database!

First install poetry if you don't have it, and then install all the dependencies:

```bash
pip install poetry
poetry install
``` 

To run all the tests:

```bash
poetry run pytest -v
```

If you only want to run tests against fake redis, without a real redis::

```bash
poetry run pytest -m fake
```

Because this module is attempting to provide the same interface as `redis-py`,
the python bindings to redis, a reasonable way to test this to take each
unittest and run it against a real redis server. fakeredis and the real redis
server should give the same result. To run tests against a real redis instance
instead:

```bash
poetry run pytest -m real
```

If redis is not running, and you try to run tests against a real redis server,
these tests will have a result of 's' for skipped.

There are some tests that test redis blocking operations that are somewhat
slow. If you want to skip these tests during day to day development,
they have all been tagged as 'slow' so you can skip them by running:

```bash
poetry run pytest -m "not slow"
```

## Contributing

Contributions are welcome.
You can contribute in many ways:
Open issues for bugs you found, implementing a command which is not yet implemented,
implement a test for scenario that is not covered yet, write a guide how to use fakeredis, etc.

Please see the [contributing guide](./about/contributing.md) for more details.
If you'd like to help out, you can start with any of the issues labeled with `Help wanted`.

There are guides how to [implement a new command](#implementing-support-for-a-command) and
how to [write new test cases](#write-a-new-test-case).

New contribution guides are welcome.

## Sponsor

fakeredis-py is developed for free.

You can support this project by becoming a sponsor using [this link](https://github.com/sponsors/cunla).
