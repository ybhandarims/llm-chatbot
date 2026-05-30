const { test } = require('node:test');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');

function makeMockFetch() {
  return (url, options) => {
    const u = String(url);
    if (u.endsWith('/settings')) {
      return Promise.resolve({ ok: true, json: async () => ({ system_prompt: 'You are a helpful assistant.' }) });
    }
    if (u.endsWith('/conversations')) {
      return Promise.resolve({ ok: true, json: async () => ([{ id: 'conv1', title: 'Demo', last_message_preview: 'Hello' }]) });
    }
    if (u.includes('/conversations/')) {
      return Promise.resolve({ ok: true, json: async () => ({ id: 'conv1', messages: [{ role: 'user', content: 'hello' }] }) });
    }
    if (u.endsWith('/chat/send')) {
      return Promise.resolve({ ok: true, json: async () => ({ conversation: { id: 'conv1', messages: [{ role: 'assistant', content: 'Echo' }, { role: 'user', content: 'hello' }] } }) });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  };
}

test('chat form submit sends message and updates UI', async () => {
  let indexHtml = fs.readFileSync(path.join(__dirname, '..', 'public', 'index.html'), 'utf8');
  const appJs = fs.readFileSync(path.join(__dirname, '..', 'public', 'assets', 'app.js'), 'utf8');
  indexHtml = indexHtml.replace('<link rel="stylesheet" href="/assets/styles.css" />', '');
  indexHtml = indexHtml.replace('<script src="/assets/app.js" defer></script>', `<script>${appJs}</script>`);

  const dom = new JSDOM(indexHtml, {
    runScripts: 'dangerously',
    resources: 'usable',
    url: 'http://localhost',
    beforeParse(window) {
      window.fetch = makeMockFetch();
      window.__API_BASE__ = '';
    },
  });

  // wait for bootstrap
  await new Promise((resolve) => {
    dom.window.addEventListener('load', () => setTimeout(resolve, 50));
  });

  const messageInput = dom.window.document.getElementById('message-input');
  const chatForm = dom.window.document.getElementById('chat-form');

  messageInput.value = 'hello';

  // submit the form
  const submitEvent = new dom.window.Event('submit', { bubbles: true, cancelable: true });
  chatForm.dispatchEvent(submitEvent);

  // allow async sendMessage to complete
  await new Promise((r) => setTimeout(r, 100));

  const messages = dom.window.document.getElementById('messages');
  // after send, messages should include assistant reply 'Echo'
  const texts = Array.from(messages.children).map((n) => n.textContent.trim());
  assert.ok(texts.some((t) => t.includes('Echo')),
    `Expected assistant reply in messages, got: ${texts.join('|')}`);
});
