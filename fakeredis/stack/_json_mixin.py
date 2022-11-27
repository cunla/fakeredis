"""Command mixin for emulating `redis-py`'s JSON functionality."""

# Future Imports
from __future__ import annotations

# Standard Library Imports
import json
import re
from functools import partial
from itertools import filterfalse
from json import JSONDecodeError
from typing import Any, Optional, Union

from jsonpath_ng import Root, JSONPath
from jsonpath_ng.ext import parse
from redis.commands.json.commands import JsonType

from fakeredis import _helpers as helpers, _msgs as msgs
from fakeredis._commands import Key, command, delete_keys
from fakeredis._helpers import SimpleError, casematch


def _parse_jsonpath(path: Union[str, bytes]):
    """Format the supplied JSON path value."""
    if isinstance(path, bytes):
        path = path.decode()
    re_path = path_pattern.sub("$", path)
    return parse(re_path)


def _path_is_root(path: JSONPath) -> bool:
    return path == Root()


path_pattern: re.Pattern = re.compile(r"^((?<!\$)\.|(\$\.$))")
is_no_escape = partial(helpers.casematch, b"noescape")
is_not_no_escape = partial(filterfalse, is_no_escape)


def _format_path(path) -> str:
    if isinstance(path, bytes):
        path = path.decode()
    return path_pattern.sub("$", path)


class JSONObject:
    """Argument converter for JSON objects."""

    DECODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE
    ENCODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Deserialize the supplied bytes into a valid Python object."""
        try:
            return json.loads(value or b"null")
        except JSONDecodeError:
            raise SimpleError(cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Serialize the supplied Python object into a valid, JSON-formatted
        byte-encoded string."""
        return json.dumps(value, default=str).encode()


class JSONCommandsMixin:
    """`CommandsMixin` for enabling RedisJSON compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name=["JSON.DEL", "JSON.FORGET"], fixed=(Key(),), repeat=(bytes,), )
    def json_del(self, key, path_str) -> int:
        """Delete the JSON value stored at key `key` under `path`.

        For more information see `JSON.DEL
        <https://redis.io/commands/json.del>`_.
        """
        if key.value is None:
            return 0

        path = _parse_jsonpath(path_str)

        if _path_is_root(path):
            delete_keys(key)
            return 1
        found_matches = path.find(key.value)
        new_value = path.update_or_create(key.value, None)
        key.update(new_value)

        return len(found_matches)

    @staticmethod
    def _get_single(key, path_str):
        path = _parse_jsonpath(path_str)
        res = path.find(key.value)
        return res

    @command(name="JSON.GET", fixed=(Key(),), repeat=(bytes,), )
    def json_get(self, key, *args) -> bytes:
        """Get the object stored as a JSON value at key `name`.

        `args` is zero or more paths, and defaults to root path
        ``no_escape` is a boolean flag to add no_escape option to get
        non-ascii characters

        For more information see `JSON.GET <https://redis.io/commands/json.get>`_.
        """
        formatted_paths = [
            _format_path(arg)
            for arg in args
            if not casematch(b'noescape', arg)
        ]
        # Parse the sanitized paths into `jsonpath.JSONPath` objects
        resolved_paths = [self._get_single(key, path) for path in formatted_paths]

        path_values = list()  # [JSONObject.encode(p.value) for p in resolved_paths]
        for lst in resolved_paths:
            if len(lst) == 0:
                path_values.append([])
            elif len(lst) > 1 or len(resolved_paths) > 1:
                path_values.append([i.value for i in lst])
            else:
                path_values.append(lst[0].value)

        # Emulate the behavior of `redis-py`:
        #   - if only one path was supplied => return a single value
        #   - if more than one path was specified => return one value for each specified path
        if len(path_values) == 1:
            return JSONObject.encode(path_values[0])

        return JSONObject.encode(dict(zip(formatted_paths, path_values)))

    @command(name="JSON.SET", fixed=(Key(), bytes, JSONObject), repeat=(bytes,), )
    def json_set(
            self,
            key,
            path_str: bytes,
            value: JsonType,
            *args
    ) -> Optional[helpers.SimpleString]:
        """Set the JSON value at key `name` under the `path` to `obj`.

        if `flag` is b"NX", set `value` only if it does not exist.
        if `flag` is b"XX", set `value` only if it exists.

        For the purpose of using this within a pipeline, this command is also
        aliased to JSON.SET.

        For more information see `JSON.SET <https://redis.io/commands/json.set>`_.
        """
        path = _parse_jsonpath(path_str)
        if key.value is not None and (type(key.value) is not dict) and not _path_is_root(path):
            raise SimpleError(msgs.JSON_WRONG_REDIS_TYPE)
        old_value = path.find(key.value)
        nx, xx = False, False
        i = 0
        while i < len(args):
            if casematch(args[i], b'nx'):
                nx = True
                i += 1
            elif casematch(args[i], b'xx'):
                xx = True
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if xx and nx:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if (nx and old_value) or (xx and not old_value):
            return None
        new_value = path.update_or_create(key.value, value)
        key.update(new_value)

        return helpers.OK

    def json_mget(self, *args):
        pass
