import logging
import os
from textwrap import dedent
from typing import Any, Dict, List

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    JobRequest,
    MetricsCollectedEvent,
    RoomIO,
    WorkerOptions,
    cli,
    inference,
    metrics,
)
from livekit.agents.llm import ChatContext, ChatMessage, StopResponse
from livekit.plugins import silero
from supabase import Client, create_client

logger = logging.getLogger("wordpan-voice-agent")

load_dotenv(".env.local")

PROMPT_BASE = dedent(
    """
    You are a friendly language tutor helping the user practice vocabulary using a
    spoken translation game.

    The game works like this:
    - You say an English word and ask: "How do you say '<english_word>' in the target language?"
    - The user answers in the target language.
    - You check their answer against the correct translation.
    - If the answer is correct, briefly confirm and repeat the English + target word.
    - If the answer is incorrect, gently correct them and say the right translation.
    - Then immediately move on to the next word.

    After each answer, you MUST:
    - Briefly say whether the answer was correct or incorrect.
    - Say the correct translation.
    - Immediately ask for the NEXT word from your vocabulary list.

    Keep each turn short (ideally under 15–20 seconds of speech) and very focused on
    a single word.

    Important behavior:
    - Be encouraging and positive.
    - Do not over-explain grammar unless the user explicitly asks.
    - The game must CONTINUE WORD BY WORD until the user clearly says they want to stop
      (for example: "stop", "I want to stop", "结束了").
    - When the user asks to stop, briefly summarize how they did and end the session.

    You have access to a list of (english_word -> target_translation) pairs for this
    session. Use ONLY those words for the quiz, one at a time, and cycle through them
    in order (or randomly) until the user asks you to stop.
    """
)


def _create_supabase_client_from_env() -> Client | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_ANON_KEY is not set; falling back to built-in words.")
        return None
    try:
        return create_client(url, key)
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc)
        return None


def _load_public_word_pairs(limit: int = 100) -> List[Dict[str, str]]:
    """
    Load a global/public vocabulary list from the word_pairs table.

    We intentionally use rows where user_id IS NULL so this acts as a shared deck
    for all learners, without needing a per-user JWT inside the agent.
    """
    client = _create_supabase_client_from_env()
    if client is None:
        return []

    try:
        resp = (
            client.table("word_pairs")
            .select("word1, word2")
            .is_("user_id", None)  # public / global deck
            .limit(limit)
            .execute()
        )
        data: List[Dict[str, Any]] = resp.data or []
        words: List[Dict[str, str]] = []
        for row in data:
            w1 = (row.get("word1") or "").strip()
            w2 = (row.get("word2") or "").strip()
            if not w1 or not w2:
                continue
            words.append({"english": w1, "target": w2})
        return words
    except Exception as exc:
        logger.error("Failed to load word_pairs from Supabase: %s", exc)
        return []


class VocabularyAssistant(Agent):
    def __init__(self, word_pairs: List[Dict[str, str]], target_language_name: str = "Portuguese") -> None:
        """
        word_pairs: list of {"english": ..., "target": ...} dictionaries.

        The LLM will use these as the source of quiz questions.
        """
        # Include a compact description of the vocabulary list in the system prompt
        if word_pairs:
            preview_pairs = ", ".join(
                f"{w['english']} → {w['target']}" for w in word_pairs[:20]
            )
            vocab_hint = dedent(
                f"""

                Vocabulary for this session (english → {target_language_name}):
                {preview_pairs}

                Use only these pairs during the game. When you finish the list,
                you may loop back to the beginning.
                """
            )
        else:
            vocab_hint = dedent(
                f"""

                No external vocabulary list is available. Instead, you should pick
                simple and useful English words and translate them into {target_language_name}
                yourself, still following the same quiz pattern.
                """
            )

        instructions = PROMPT_BASE + vocab_hint

        super().__init__(instructions=instructions)
        self._word_pairs = word_pairs

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        if not new_message.text_content:
            logger.info("ignore empty user turn")
            raise StopResponse()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Load shared/public vocabulary from Supabase once per worker job
    word_pairs = _load_public_word_pairs(limit=100)
    logger.info("Loaded %d word pairs for voice quiz", len(word_pairs))

    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts=inference.TTS(
            model="cartesia/sonic-2",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            language="en",
        ),
        # Rely on the STT provider's endpointing to determine when user turns end.
        # Do not override turn_detection here to keep multi-turn behavior stable.
    )

    room_io = RoomIO(session, room=ctx.room)
    await room_io.start()

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent) -> None:
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage() -> None:
        summary = usage_collector.get_summary()
        logger.info("Usage: %s", summary)

    ctx.add_shutdown_callback(log_usage)

    assistant = VocabularyAssistant(word_pairs=word_pairs)

    await session.start(agent=assistant)

    # Connect to the room before accessing local_participant or registering RPCs.
    await ctx.connect()

    # Tell RoomIO which remote participant we should listen to.
    def _set_primary_participant() -> None:
        # Prefer the first remote participant, assuming a 1:1 room.
        for p in ctx.room.remote_participants.values():
            room_io.set_participant(p.identity)
            logger.info("listening to participant %s", p.identity)
            return

    _set_primary_participant()

    @ctx.room.on("participant_connected")
    def _on_participant_connected(participant: rtc.RemoteParticipant) -> None:
        # When a participant connects after the agent, start listening to them.
        room_io.set_participant(participant.identity)
        logger.info("participant connected, now listening to %s", participant.identity)

    # Enable audio input so the agent can hear the user.
    session.input.set_audio_enabled(True)

    async def _start_quiz() -> None:
        """Internal helper to kick off the vocabulary game with an intro turn."""
        if assistant._word_pairs:
            intro = (
                "Let's start our vocabulary game! I have a list of English words "
                "and their translations in your target language. "
                "I will say an English word and you answer with the translation. "
                "I'll tell you if it's correct and then move on to the next word."
            )
        else:
            intro = (
                "Let's start our vocabulary game! I will pick simple English words "
                "and you answer with the translation in your target language. "
                "I'll tell you if it's correct and then move on to the next word."
            )

        logger.info("starting quiz intro turn")
        session.generate_reply(user_input=intro)

    # Optional RPC: frontend can call this to explicitly start the game.
    @ctx.room.local_participant.register_rpc_method("start_game")
    async def start_game(data: rtc.RpcInvocationData) -> None:
        """
        Frontend can call this RPC once the room is connected to explicitly
        start the quiz loop. The detailed behavior (asking, judging, moving
        to next word) is handled by the LLM using the vocabulary list from
        the system prompt.
        """
        del data  # unused for now
        logger.info("start_game RPC called")
        await _start_quiz()

    # Auto-start the game with a greeting so the user hears something
    # shortly after connecting, even if the frontend does not call start_game.
    await _start_quiz()


async def handle_request(request: JobRequest) -> None:
    await request.accept(
        identity="wordpan-vocab-agent",
        attributes={"push-to-talk": "1"},
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=handle_request,
            prewarm_fnc=prewarm,
            agent_name="wordpan-voice-agent",
        )
    )

