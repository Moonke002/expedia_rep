<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { loadChatConversation, sendChatMessage } from '../api/chat.js'

const CONVERSATION_STORAGE_KEY = 'expedia-rep-chat-conversation'
const isOpen = ref(false)
const draft = ref('')
const messages = ref([])
const pending = ref(false)
const error = ref('')
const conversationId = ref(localStorage.getItem(CONVERSATION_STORAGE_KEY) || '')
const conversationElement = ref(null)
let nextMessageId = 0

async function scrollConversationToBottom() {
  await nextTick()
  if (conversationElement.value) {
    conversationElement.value.scrollTop = conversationElement.value.scrollHeight
  }
}

async function openAssistant() {
  isOpen.value = true
  await scrollConversationToBottom()
}

function saveConversationId(id) {
  conversationId.value = id
  localStorage.setItem(CONVERSATION_STORAGE_KEY, id)
}

function clearConversationId() {
  conversationId.value = ''
  localStorage.removeItem(CONVERSATION_STORAGE_KEY)
}

function toDisplayMessage(item) {
  nextMessageId = Math.max(nextMessageId, item.message_id ?? 0)
  return {
    id: item.message_id ?? ++nextMessageId,
    role: item.role,
    text: item.content,
    createdAt: item.created_at,
    proposedSql: item.proposed_sql,
    records: item.retrieved_records ?? [],
  }
}

async function restoreConversation() {
  if (!conversationId.value) return
  const history = await loadChatConversation(conversationId.value)
  messages.value = history.messages.map(toDisplayMessage)
  await scrollConversationToBottom()
}

onMounted(async () => {
  try {
    await restoreConversation()
  } catch (loadError) {
    if (loadError.status === 404) clearConversationId()
    else error.value = loadError.message || 'Saved conversation history could not be loaded.'
  }
})

function timestampLabel(value) {
  return value ? new Date(value).toLocaleString() : ''
}

async function sendMessage() {
  const message = draft.value.trim()
  if (!message || pending.value) return

  error.value = ''
  pending.value = true
  const userMessage = { id: ++nextMessageId, role: 'user', text: message }
  messages.value.push(userMessage)
  await scrollConversationToBottom()

  try {
    const result = await sendChatMessage(message, conversationId.value || null)
    saveConversationId(result.conversationId)
    messages.value.push({
      id: ++nextMessageId,
      role: 'assistant',
      text: result.reply,
      proposedSql: result.proposedSql,
      records: result.records,
    })
    await scrollConversationToBottom()
    draft.value = ''
    try {
      await restoreConversation()
    } catch {
      // The successful response remains visible if the history refresh itself fails.
    }
  } catch (requestError) {
    if (requestError.conversationId) {
      saveConversationId(requestError.conversationId)
      try {
        await restoreConversation()
      } catch {
        messages.value.push({
          id: ++nextMessageId,
          role: 'error',
          text: requestError.message || 'The travel assistant could not answer right now.',
        })
      }
      error.value = ''
    } else {
      if (requestError.status === 404) clearConversationId()
      messages.value = messages.value.filter((item) => item.id !== userMessage.id)
      error.value = requestError.message || 'The travel assistant could not answer right now.'
    }
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="travel-chat-widget">
    <button
      v-if="!isOpen"
      class="chat-launcher"
      type="button"
      aria-label="Open travel assistant"
      aria-controls="travel-assistant-panel"
      :aria-expanded="isOpen"
      @click="openAssistant"
    >
      <span class="chat-launcher-icon" aria-hidden="true">✦</span>
      <span>Ask the travel assistant</span>
    </button>

    <section
      v-else
      id="travel-assistant-panel"
      class="chat-popover"
      role="dialog"
      aria-modal="false"
      aria-labelledby="assistant-title"
      @keydown.esc="isOpen = false"
    >
      <header class="chat-popover-header">
        <div>
          <p class="eyebrow">Grounded in the local demo catalog</p>
          <h2 id="assistant-title">Travel assistant</h2>
        </div>
        <button class="chat-close" type="button" aria-label="Close travel assistant" @click="isOpen = false">×</button>
      </header>
      <p class="assistant-intro">Ask about saved API hotels, ZIP locations, and dated simulated nightly rates and availability.</p>
      <p v-if="conversationId" class="chat-conversation-id">Conversation ID: <code>{{ conversationId }}</code></p>

      <div ref="conversationElement" class="chat-conversation" aria-live="polite" aria-label="Conversation">
        <p v-if="messages.length === 0" class="chat-empty">Ask about saved hotels, locations, stay dates, prices, or simulated room availability.</p>
        <article
          v-for="item in messages"
          :key="item.id"
          class="chat-message"
          :class="`chat-message-${item.role}`"
        >
          <h3>{{ item.role === 'user' ? 'You' : item.role === 'error' ? 'Request failed' : 'Travel assistant' }}</h3>
          <time v-if="item.createdAt" :datetime="item.createdAt">{{ timestampLabel(item.createdAt) }}</time>
          <p>{{ item.text }}</p>
          <details v-if="item.role === 'assistant' || item.proposedSql" class="chat-evidence" :open="item.role === 'error'">
            <summary>{{ item.role === 'error' ? 'Show rejected SQL proposal' : `Show proposed SQL and retrieved records (${item.records.length})` }}</summary>
            <h4>{{ item.role === 'error' ? 'Proposed SQL (blocked before retrieval)' : 'Proposed SQL (validated, read-only)' }}</h4>
            <pre>{{ item.proposedSql }}</pre>
            <template v-if="item.role === 'assistant'">
              <h4>Retrieved SQLite records</h4>
              <pre>{{ JSON.stringify(item.records, null, 2) }}</pre>
              <p v-if="item.records.length === 0" class="chat-empty-records">No matching records were returned.</p>
            </template>
          </details>
        </article>
        <p v-if="pending" class="chat-pending" role="status">Sending your message and waiting for a reply…</p>
      </div>

      <form class="assistant-form" @submit.prevent="sendMessage">
        <label for="chat-message">Message</label>
        <textarea
          id="chat-message"
          v-model="draft"
          rows="3"
          maxlength="500"
          required
          placeholder="Which stays are available in State College?"
          :disabled="pending"
        ></textarea>
        <div class="assistant-form-footer">
          <span>{{ draft.length }}/500</span>
          <button class="primary-button" type="submit" :disabled="pending || !draft.trim()">
            {{ pending ? 'Sending…' : 'Send' }}
          </button>
        </div>
      </form>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p class="assistant-disclaimer">Demo catalog facts only. No live inventory or bookings.</p>
    </section>
  </div>
</template>
