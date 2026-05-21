const API_BASE =
  window.__API_BASE__ ||
  (window.location.hostname === "localhost" && window.location.port === "3000"
    ? "http://localhost:8080/api"
    : "/api");

const els = {
  conversationList: document.getElementById("conversation-list"),
  messages: document.getElementById("messages"),
  status: document.getElementById("status"),
  systemPromptInput: document.getElementById("system-prompt-input"),
  savePromptBtn: document.getElementById("save-prompt-btn"),
  chatForm: document.getElementById("chat-form"),
  messageInput: document.getElementById("message-input"),
  newChatBtn: document.getElementById("new-chat-btn"),
};

let state = {
  currentConversationId: null,
  conversations: [],
};

function setStatus(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("error", isError);
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMessages(messages) {
  els.messages.innerHTML = "";
  for (const message of messages) {
    const div = document.createElement("div");
    div.className = `message ${message.role}`;
    div.innerHTML = escapeHtml(message.content);
    els.messages.appendChild(div);
  }
  els.messages.scrollTop = els.messages.scrollHeight;
}

function showTypingIndicator() {
  const typing = document.createElement("div");
  typing.className = "message assistant typing";
  typing.innerHTML = `
    <span class="typing-dots" aria-label="Assistant is typing">
      <span></span><span></span><span></span>
    </span>
    <span class="typing-text">Assistant is typing...</span>
  `;
  els.messages.appendChild(typing);
  els.messages.scrollTop = els.messages.scrollHeight;
  return typing;
}

function renderConversations() {
  els.conversationList.innerHTML = "";
  for (const conversation of state.conversations) {
    const item = document.createElement("li");
    item.className = "conversation-item";
    if (conversation.id === state.currentConversationId) {
      item.classList.add("active");
    }
    item.innerHTML = `
      <div class="conversation-title">${escapeHtml(conversation.title)}</div>
      <div class="conversation-preview">${escapeHtml(conversation.last_message_preview || "No messages yet")}</div>
    `;
    item.addEventListener("click", () => openConversation(conversation.id));
    els.conversationList.appendChild(item);
  }
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json();
}

async function loadSystemPrompt() {
  const payload = await apiFetch("/settings");
  document.getElementById('system-prompt-input').value = payload.system_prompt || payload.system_prompt || '';
}

async function loadConversations() {
  state.conversations = await apiFetch("/conversations");
  renderConversations();
}

async function openConversation(conversationId) {
  setStatus("Loading conversation...");
  const detail = await apiFetch(`/conversations/${conversationId}`);
  state.currentConversationId = detail.id;
  renderConversations();
  renderMessages(detail.messages || []);
  setStatus("Ready");
}

async function sendMessage(messageText) {
  setStatus("Sending...");
  const typingIndicator = showTypingIndicator();
  const payload = await apiFetch("/chat/send", {
    method: "POST",
    body: JSON.stringify({
      message: messageText,
      conversation_id: state.currentConversationId,
    }),
  });

  state.currentConversationId = payload.conversation.id;
  await loadConversations();

  typingIndicator.remove();
  renderMessages(payload.conversation.messages || []);
  setStatus("Ready");
}

async function saveSystemPrompt() {
  setStatus("Saving prompt...");
  await apiFetch("/settings", {
    method: "POST",
    body: JSON.stringify({ system_prompt: document.getElementById('system-prompt-input').value.trim() }),
  });
  setStatus("System prompt updated");
}

function registerEvents() {
  els.chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = els.messageInput.value.trim();
    if (!text) {
      return;
    }
    els.messageInput.value = "";
    try {
      await sendMessage(text);
    } catch (error) {
      setStatus(error.message || "Could not send message", true);
    }
  });

  els.savePromptBtn.addEventListener("click", async () => {
    try {
      await saveSystemPrompt();
    } catch (error) {
      setStatus(error.message || "Could not save prompt", true);
    }
  });

  els.newChatBtn.addEventListener("click", () => {
    (async () => {
      try {
        state.currentConversationId = null;
        renderMessages([]);
        renderConversations();
        setStatus("New chat ready");
      } catch (err) {
        setStatus(err.message || "Could not create conversation", true);
      }
    })();
  });
}

async function bootstrap() {
  registerEvents();
  try {
    await loadSystemPrompt();
    await loadConversations();
    if (state.conversations.length > 0) {
      await openConversation(state.conversations[0].id);
    }
  } catch (error) {
    setStatus(error.message || "Failed to initialize", true);
  }
}

bootstrap();
