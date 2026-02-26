import { useEffect, useState } from "react"
import { LiveKitRoom, RoomAudioRenderer, StartAudio, useVoiceAssistant } from "@livekit/components-react"
import { getLivekitToken } from "@/lib/ai-service"

type AgentStatusState = ReturnType<typeof useVoiceAssistant>["state"]

function AgentStatus() {
  const { state } = useVoiceAssistant()

  let label: string
  switch (state as AgentStatusState) {
    case "connecting":
      label = "Connecting..."
      break
    case "listening":
      label = "Listening to you"
      break
    case "thinking":
      label = "Thinking"
      break
    case "speaking":
      label = "Speaking"
      break
    default:
      label = "Idle"
  }

  return (
    <p className="text-sm text-muted-foreground">
      Agent state: <span className="font-medium">{label}</span>
    </p>
  )
}

export default function VoicePracticePage() {
  const [sessionStarted, setSessionStarted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [roomName, setRoomName] = useState<string | null>(null)

  const handleStart = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const resp = await getLivekitToken()
      setLivekitUrl(resp.url)
      setToken(resp.token)
      setRoomName(resp.roomName)
      setSessionStarted(true)
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to start voice session"
      setError(message)
      setSessionStarted(false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStop = () => {
    setSessionStarted(false)
    setToken(null)
    setRoomName(null)
  }

  // If there is no token/url yet, we don't render the LiveKitRoom
  const shouldConnect = sessionStarted && !!token && !!livekitUrl

  // When the room is connected, the frontend can trigger the agent's "start_game" RPC
  // using LiveKit RPC APIs if desired. For now, the agent will greet and start the quiz
  // based on its system instructions when the user speaks.

  return (
    <div className="flex flex-col gap-6 px-4 lg:px-6">
      <header className="mt-4 space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Voice Vocabulary Practice</h1>
        <p className="text-muted-foreground max-w-2xl">
          Practice translating words by speaking your answers aloud. When you start the game, a voice
          agent will join and begin quizzing you on word translations pulled from your WordPan vocabulary.
        </p>
      </header>

      <div className="flex items-center gap-4">
        {sessionStarted ? (
          <button
            type="button"
            className="inline-flex items-center rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground shadow-sm hover:opacity-90"
            onClick={handleStop}
            disabled={isLoading}
          >
            Stop Session
          </button>
        ) : (
          <button
            type="button"
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:opacity-90"
            onClick={handleStart}
            disabled={isLoading}
          >
            {isLoading ? "Starting..." : "Start Game"}
          </button>
        )}
        <span className="text-sm text-muted-foreground">
          Make sure your microphone is enabled when the game starts.
        </span>
      </div>

      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <section className="rounded-lg border bg-card p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Agent status</h2>
        {shouldConnect ? (
          <LiveKitRoom
            serverUrl={livekitUrl!}
            token={token!}
            connect={true}
            audio={true}
            video={false}
          >
            {/* Render agent audio into the page and gate playback behind a user gesture */}
            <RoomAudioRenderer />
            <div className="mb-2">
              <StartAudio label="Enable audio" />
            </div>
            <AgentStatus />
          </LiveKitRoom>
        ) : (
          <p className="text-sm text-muted-foreground">
            {sessionStarted
              ? "Connecting to the voice agent..."
              : "The voice agent is idle. Click “Start Game” to begin a new practice session."}
          </p>
        )}
        {roomName && (
          <p className="mt-2 text-xs text-muted-foreground">
            Room: <span className="font-mono">{roomName}</span>
          </p>
        )}
      </section>
    </div>
  )
}

