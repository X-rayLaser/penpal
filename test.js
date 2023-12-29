import test from 'ava';
import add from './frontend/src/tree';

test('foo', t => {
    t.assertEqual(8, add(3, 5));
	t.pass();
});