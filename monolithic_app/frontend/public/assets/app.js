const API_BASE =
  "http://127.0.0.1:8000/api";

const els = {
  conversationList: document.getElementById("conversation-list"),
  messages: document.getElementById("messages"),
  status: document.getElementById("status"),
  systemPromptInput: document.getElementById("system-prompt-input"),
  savedPromptPreview: document.getElementById("saved-prompt-preview"),
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
  const payload = await apiFetch("/settings/system-prompt");
  els.systemPromptInput.value = payload.system_prompt;
  els.savedPromptPreview.textContent = `Saved prompt: ${payload.system_prompt}`;
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
  renderMessages(detail.messages.filter((m) => m.role !== "system"));
  setStatus("Ready");
}

async function sendMessage(messageText) {
  setStatus("Sending...");
  const payload = await apiFetch("/chat/send", {
    method: "POST",
    body: JSON.stringify({
      message: messageText,
      conversation_id: state.currentConversationId,
    }),
  });

  state.currentConversationId = payload.conversation.id;
  await loadConversations();

  const detail = await apiFetch(`/conversations/${state.currentConversationId}`);
  renderMessages(detail.messages.filter((m) => m.role !== "system"));
  setStatus("Ready");
}

async function saveSystemPrompt() {
  setStatus("Saving prompt...");
  const payload = await apiFetch("/settings/system-prompt", {
    method: "PUT",
    body: JSON.stringify({ system_prompt: els.systemPromptInput.value.trim() }),
  });
  els.systemPromptInput.value = payload.system_prompt;
  els.savedPromptPreview.textContent = `Saved prompt: ${payload.system_prompt}`;
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
    state.currentConversationId = null;
    renderConversations();
    renderMessages([]);
    setStatus("New chat ready");
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
