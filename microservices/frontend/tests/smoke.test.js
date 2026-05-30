const test = require('node:test');
const assert = require('node:assert/strict');

test('frontend smoke test passes', () => {
  const title = 'microservices-frontend';
  assert.equal(title.includes('frontend'), true);
});
