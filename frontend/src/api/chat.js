async function readJson(response) {
  try {
    return await response.json()
  } catch {
    if (response.ok) throw new Error('The server returned an unreadable response.')
    return {}
  }
}

function throwForResponse(response, payload) {
  if (response.ok) return
  const error = new Error(payload.detail ?? 'The message could not be sent.')
  error.conversationId = payload.conversation_id ?? null
  error.status = response.status
  throw error
}

export async function sendChatMessage(message, conversationId = null) {
  const body = { message }
  if (conversationId) body.conversation_id = conversationId
  const response = await fetch('/api/chat', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const payload = await readJson(response)
  throwForResponse(response, payload)

  if (typeof payload.conversation_id !== 'string' || typeof payload.reply !== 'string'
      || typeof payload.proposed_sql !== 'string' || !Array.isArray(payload.records)) {
    throw new Error('The server returned an invalid chat response.')
  }

  return {
    conversationId: payload.conversation_id,
    reply: payload.reply,
    proposedSql: payload.proposed_sql,
    records: payload.records,
  }
}

export async function loadChatConversation(conversationId) {
  const response = await fetch(`/api/chat/${encodeURIComponent(conversationId)}`, {
    credentials: 'same-origin',
  })
  const payload = await readJson(response)
  throwForResponse(response, payload)
  if (payload.conversation_id !== conversationId || !Array.isArray(payload.messages)) {
    throw new Error('The server returned invalid conversation history.')
  }
  return payload
}
