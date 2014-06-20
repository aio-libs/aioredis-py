import asyncio

from ._testutil import BaseTest, run_until_complete
from aioredis import create_redis, ReplyError, WrongArgumentError


class StringCommandsTest(BaseTest):

    def setUp(self):
        super().setUp()
        self.redis = self.loop.run_until_complete(create_redis(
            ('localhost', self.redis_port), loop=self.loop))

    def tearDown(self):
        self.redis.close()
        del self.redis
        super().tearDown()

    @asyncio.coroutine
    def add(self, key, value):
        ok = yield from self.redis.connection.execute('set', key, value)
        self.assertEqual(ok, b'OK')

    @run_until_complete
    def test_append(self):
        len_ = yield from self.redis.append('my-key', 'Hello')
        self.assertEqual(len_, 5)
        len_ = yield from self.redis.append('my-key', ', world!')
        self.assertEqual(len_, 13)

        val = yield from self.redis.connection.execute('GET', 'my-key')
        self.assertEqual(val, b'Hello, world!')

        with self.assertRaises(TypeError):
            yield from self.redis.append(None, 'value')
        with self.assertRaises(ReplyError):
            yield from self.redis.append('none-key', None)

    @run_until_complete
    def test_get(self):
        yield from self.add('my-key', 'value')
        ret = yield from self.redis.get('my-key')
        self.assertEqual(ret, b'value')

        yield from self.add('my-key', 123)
        ret = yield from self.redis.get('my-key')
        self.assertEqual(ret, b'123')

        ret = yield from self.redis.get('bad-key')
        self.assertIsNone(ret)

        with self.assertRaises(TypeError):
            yield from self.redis.get(None)

    @run_until_complete
    def test_set(self):
        ok = yield from self.redis.set('my-key', 'value')
        self.assertEqual(ok, b'OK')

        with self.assertRaises(TypeError):
            yield from self.redis.set(None, 'value')

    @run_until_complete
    def test_bitcount(self):
        key, value = b'key:bitcount', b'foobar'
        yield from self.add(key, value)
        test_value = yield from self.redis.bitcount(key, 0, 0)
        self.assertEqual(test_value, 4)
        test_value = yield from self.redis.bitcount(key, 1, 1)
        self.assertEqual(test_value, 6)

    @run_until_complete
    def test_bitop_string(self):
        key1, value1 = b'key:bitop:str:1', b'foo'
        key2, value2 = b'key:bitop:str:2', b'bar'

        yield from self.add(key1, value1)
        yield from self.add(key2, value2)

        destkey = b'key:bitop:dest'

        yield from self.redis.bitop('AND', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'bab')

        yield from self.redis.bitop('OR', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'fo\x7f')

        yield from self.redis.bitop('XOR', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'\x04\x0e\x1d')

        yield from self.redis.bitop('NOT', destkey, key1)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'\x99\x90\x90')

    @run_until_complete
    def test_bitop_int(self):
        key1, value1 = b'key:bitop:int:1', 5
        key2, value2 = b'key:bitop:int:2', 7

        yield from self.add(key1, value1)
        yield from self.add(key2, value2)

        destkey = b'key:bitop:dest'

        yield from self.redis.bitop('AND', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'5')

        yield from self.redis.bitop('OR', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'7')

        yield from self.redis.bitop('XOR', destkey, key1, key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'\x02')

        yield from self.redis.bitop('XOR', destkey, key1, b'not:' + key2)
        test_value = yield from self.redis.get(destkey)
        self.assertEqual(test_value, b'5')

    @run_until_complete
    def test_bitop_wrong_args(self):
        key1, value1 = b'key:bitop:1', 5
        key2, value2 = b'key:bitop:2', 7

        yield from self.add(key1, value1)
        yield from self.add(key2, value2)

        destkey = b'key:bitop:dest'

        with self.assertRaises(WrongArgumentError):
            yield from self.redis.bitop('XXX', destkey, key1, key2)

        with self.assertRaises(WrongArgumentError):
            yield from self.redis.bitop('NOT', destkey, key1, key2)

        with self.assertRaises(WrongArgumentError):
            yield from self.redis.bitop('OR', destkey, key1)

        for op in {'AND', 'OR', 'XOR'}:
            with self.assertRaises(WrongArgumentError):
                yield from self.redis.bitop(op, destkey, key1)

    @run_until_complete
    def test_bitpos(self):
        key, value = b'key:bitop', b'\xff\xf0\x00'
        yield from self.add(key, value)
        test_value = yield from self.redis.bitpos(key, 0)
        self.assertEqual(test_value, 12)

        test_value = yield from self.redis.bitpos(key, 0, 2, 3)
        self.assertEqual(test_value, 16)

        key, value = b'key:bitop', b'\x00\xff\xf0'
        yield from self.add(key, value)
        test_value = yield from self.redis.bitpos(key, 1, 0)
        self.assertEqual(test_value, 8)

        test_value = yield from self.redis.bitpos(key, 1, 1)
        self.assertEqual(test_value, 8)

        key, value = b'key:bitop', b'\x00\x00\x00'
        yield from self.add(key, value)
        test_value = yield from self.redis.bitpos(key, 1, 0)
        self.assertEqual(test_value, -1)

        test_value = yield from self.redis.bitpos(b'not:' + key, 1)
        self.assertEqual(test_value, -1)

        with self.assertRaises(WrongArgumentError):
            test_value = yield from self.redis.bitpos(key, 1, end=1)

        with self.assertRaises(WrongArgumentError):
            test_value = yield from self.redis.bitpos(key, 7)

    @run_until_complete
    def test_decr(self):
        key, value = b'key:decr', 10
        yield from self.add(key, value)
        test_value = yield from self.redis.decr(key)
        self.assertEqual(test_value, 9)

        yield from self.add(key, -10)
        test_value = yield from self.redis.decr(key)
        self.assertEqual(test_value, -11)

        with self.assertRaises(ReplyError):
            yield from self.add(key, 234293482390480948029348230948)
            test_value = yield from self.redis.decr(key)

        with self.assertRaises(ReplyError):
            yield from self.add(key, 3.14)
            test_value = yield from self.redis.decr(key)

        with self.assertRaises(ReplyError):
            yield from self.add(key, "pi")
            test_value = yield from self.redis.decr(key)

        with self.assertRaises(TypeError):
            yield from self.add(key, 10)
            test_value = yield from self.redis.decr(None)

    @run_until_complete
    def test_decrby(self):
        key, value = b'key:decrby', 10
        yield from self.add(key, value)
        test_value = yield from self.redis.decrby(key, 3)
        self.assertEqual(test_value, 7)

        yield from self.add(key, -10)
        test_value = yield from self.redis.decrby(key, -3)
        self.assertEqual(test_value, -7)

        with self.assertRaises(ReplyError):
            yield from self.add(key, 234293482390480948029348230948)
            test_value = yield from self.redis.decrby(key, 10)

        with self.assertRaises(ReplyError):
            yield from self.add(key, 3.14)
            test_value = yield from self.redis.decrby(key, 2)

        with self.assertRaises(ReplyError):
            yield from self.add(key, "pi")
            test_value = yield from self.redis.decrby(key, 5)

        with self.assertRaises(TypeError):
            yield from self.add(key, 10)
            test_value = yield from self.redis.decrby(None)

        with self.assertRaises(ReplyError):
            yield from self.add(key, 10)
            test_value = yield from self.redis.decrby(key, 2.0)
