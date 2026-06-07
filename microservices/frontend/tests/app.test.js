const { test } = require("node:test");
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const assert = require("node:assert/strict");

function makeMockFetch() {
  return (url, options) => {
    const u = String(url);
    if (u.endsWith("/settings")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ system_prompt: "You are a helpful assistant." }),
      });
    }
    if (u.endsWith("/conversations")) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          { id: "conv1", title: "Demo", last_message_preview: "Hello" },
        ],
      });
    }
    if (u.includes("/conversations/")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: "conv1",
          messages: [{ role: "user", content: "hello" }],
        }),
      });
    }
    if (u.endsWith("/chat/send")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          conversation: {
            id: "conv1",
            messages: [{ role: "assistant", content: "Echo" }],
          },
        }),
      });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  };
}

test("app bootstrap loads UI and renders conversations/messages", async () => {
  let indexHtml = fs.readFileSync(
    path.join(__dirname, "..", "public", "index.html"),
    "utf8",
  );
  // Inline app.js and remove external CSS to avoid network requests in JSDOM
  const appJs = fs.readFileSync(
    path.join(__dirname, "..", "public", "assets", "app.js"),
    "utf8",
  );
  indexHtml = indexHtml.replace(
    '<link rel="stylesheet" href="/assets/styles.css" />',
    "",
  );
  indexHtml = indexHtml.replace(
    '<script src="/assets/app.js" defer></script>',
    `<script>${appJs}</script>`,
  );

  const dom = new JSDOM(indexHtml, {
    runScripts: "dangerously",
    resources: "usable",
    url: "http://localhost",
    beforeParse(window) {
      // provide a minimal fetch implementation the app expects
      window.fetch = makeMockFetch();
      // ensure the API base resolves locally
      window.__API_BASE__ = "";
    },
  });

  // Wait for scripts to load and app bootstrap to complete
  await new Promise((resolve) => {
    dom.window.addEventListener("load", () => {
      // allow some time for async bootstrap calls
      setTimeout(resolve, 50);
    });
  });

  const status = dom.window.document.getElementById("status").textContent;
  assert.ok(
    status === "Ready" ||
      status === "New chat ready" ||
      status === "System prompt updated",
  );

  const convoList = dom.window.document.getElementById("conversation-list");
  assert.ok(
    convoList.children.length >= 1,
    "Conversation list should render at least one item",
  );

  const messages = dom.window.document.getElementById("messages");
  assert.ok(
    messages.children.length >= 1,
    "Messages should render at least one message",
  );
});
