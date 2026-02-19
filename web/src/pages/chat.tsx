import { useEffect, useMemo, useState } from 'react'
import { useUser } from '@/contexts/UserContext'
import { supabase } from '@/lib/supabase'
import type { Database } from '@/lib/database.types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

type Chat = Database['public']['Tables']['chats']['Row']
type ChatMessage = Database['public']['Tables']['chat_messages']['Row']

export default function ChatPage() {
  const { user, loading: userLoading } = useUser()
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [chatsLoading, setChatsLoading] = useState(true)
  const [creatingChat, setCreatingChat] = useState(false)
  const [deletingChatId, setDeletingChatId] = useState<string | null>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [newMessage, setNewMessage] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (!userLoading && user) {
      void fetchChats()
    }
  }, [userLoading, user])

  useEffect(() => {
    if (!selectedChatId) {
      setMessages([])
      return
    }
    void fetchMessages(selectedChatId)
  }, [selectedChatId])

  const fetchChats = async () => {
    if (!user) return
    try {
      setChatsLoading(true)
      const { data, error } = await supabase
        .from('chats')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })

      if (error) {
        console.error('Error fetching chats:', error)
        return
      }

      setChats(data || [])
      if (!selectedChatId && data && data.length > 0) {
        setSelectedChatId(data[0].id)
      }
    } catch (err) {
      console.error('Unexpected error fetching chats:', err)
    } finally {
      setChatsLoading(false)
    }
  }

  const fetchMessages = async (chatId: string) => {
    try {
      setMessagesLoading(true)
      const { data, error } = await supabase
        .from('chat_messages')
        .select('*')
        .eq('chat_id', chatId)
        .order('created_at', { ascending: true })

      if (error) {
        console.error('Error fetching messages:', error)
        return
      }

      setMessages(data || [])
    } catch (err) {
      console.error('Unexpected error fetching messages:', err)
    } finally {
      setMessagesLoading(false)
    }
  }

  const handleNewChat = async () => {
    if (!user) return
    try {
      setCreatingChat(true)
      const { data, error } = await supabase
        .from('chats')
        .insert({
          user_id: user.id,
          title: 'New chat',
        })
        .select()
        .single()

      if (error) {
        console.error('Error creating chat:', error)
        return
      }

      if (!data) return

      setChats((prev) => [data, ...prev])
      setSelectedChatId(data.id)
      setMessages([])
    } catch (err) {
      console.error('Unexpected error creating chat:', err)
    } finally {
      setCreatingChat(false)
    }
  }

  const handleDeleteChat = async (chatId: string) => {
    try {
      setDeletingChatId(chatId)
      const { error } = await supabase.from('chats').delete().eq('id', chatId)
      if (error) {
        console.error('Error deleting chat:', error)
        return
      }

      setChats((prev) => prev.filter((c) => c.id !== chatId))
      if (selectedChatId === chatId) {
        const remaining = chats.filter((c) => c.id !== chatId)
        setSelectedChatId(remaining[0]?.id ?? null)
        setMessages([])
      }
    } catch (err) {
      console.error('Unexpected error deleting chat:', err)
    } finally {
      setDeletingChatId(null)
    }
  }

  const selectedChat = useMemo(
    () => chats.find((c) => c.id === selectedChatId) ?? null,
    [chats, selectedChatId],
  )

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedChatId || !newMessage.trim()) return

    const content = newMessage.trim()

    try {
      setSending(true)
      setNewMessage('')

      const { data, error } = await supabase
        .from('chat_messages')
        .insert({
          chat_id: selectedChatId,
          role: 'user',
          content,
        })
        .select()
        .single()

      if (error) {
        console.error('Error sending message:', error)
        return
      }

      if (!data) return

      setMessages((prev) => [...prev, data])

      setChats((prev) =>
        prev
          .map((c) =>
            c.id === selectedChatId ? { ...c, updated_at: new Date().toISOString() } : c,
          )
          .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)),
      )
    } catch (err) {
      console.error('Unexpected error sending message:', err)
    } finally {
      setSending(false)
    }
  }

  if (userLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading user...
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-var(--header-height)-var(--spacing)*4)] gap-4">
      <Card className="flex h-full w-72 flex-col">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-sm font-semibold">Chats</h2>
          <Button size="sm" variant="outline" onClick={handleNewChat} disabled={creatingChat}>
            New
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {chatsLoading ? (
            <div className="p-4 text-sm text-muted-foreground">Loading chats...</div>
          ) : chats.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">
              No chats yet. Create your first chat.
            </div>
          ) : (
            <ul className="space-y-1 p-2">
              {chats.map((chat) => (
                <li key={chat.id}>
                  <button
                    type="button"
                    className={cn(
                      'flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-accent',
                      selectedChatId === chat.id && 'bg-accent',
                    )}
                    onClick={() => setSelectedChatId(chat.id)}
                  >
                    <span className="line-clamp-1">
                      {chat.title || 'Untitled chat'}
                    </span>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="ml-2 h-6 w-6 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation()
                        void handleDeleteChat(chat.id)
                      }}
                      disabled={deletingChatId === chat.id}
                      aria-label="Delete chat"
                    >
                      ×
                    </Button>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>

      <Card className="flex h-full flex-1 flex-col">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-semibold">
            {selectedChat ? selectedChat.title || 'Untitled chat' : 'Smart Tutor'}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Ask language questions, request translations, or practice the language you&apos;re
            learning.
          </p>
        </div>

        {!selectedChat && (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Create a new chat to start a conversation with your Smart Tutor.
          </div>
        )}

        {selectedChat && (
          <>
            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              {messagesLoading ? (
                <div className="text-sm text-muted-foreground">Loading messages...</div>
              ) : messages.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  This conversation is empty. Send a message to begin.
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex',
                      message.role === 'user' ? 'justify-end' : 'justify-start',
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[75%] rounded-lg px-3 py-2 text-sm',
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-foreground',
                      )}
                    >
                      {message.content}
                    </div>
                  </div>
                ))
              )}
            </div>

            <form
              onSubmit={handleSendMessage}
              className="flex items-center gap-2 border-t px-4 py-3"
            >
              <Input
                placeholder="Type your message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                disabled={sending || messagesLoading}
              />
              <Button type="submit" disabled={!newMessage.trim() || sending || messagesLoading}>
                Send
              </Button>
            </form>
          </>
        )}
      </Card>
    </div>
  )
}

