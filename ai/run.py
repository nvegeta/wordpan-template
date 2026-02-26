import asyncio
import os
import traceback
import warnings
from functools import wraps
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from livekit import api as lk_api
from supabase import create_client, Client

from crews.random_phrase_crew.crew import RandomPhraseCrew
from crews.random_phrase_crew.schemas import PhraseOutput
from crews.similar_words_crew.crew import SimilarWordsCrew
from crews.similar_words_crew.schemas import SimilarWordsOutput
from crews.tutor_router_crew.router_crew import RouterCrew
from crews.tutor_router_crew.translation_crew import TranslationCrew
from crews.tutor_router_crew.vocabulary_crew import VocabularyCrew
from crews.tutor_router_crew.generic_crew import GenericTutorCrew
from crews.tutor_router_crew.schemas import TutorMessage, RouterDecision
from crews.tutor_router_crew.tools.save_word_pair import SaveWordPairTool
from crews.tutor_router_crew.tools.check_word_pair_in_deck import CheckWordPairInDeckTool

from lib.tracer import traceable

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Initialize Flask app
app = Flask(__name__)

# Configure CORS - allow requests from localhost frontend
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative port
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "")


def require_auth(f):
    """
    Decorator to require authentication for endpoints.
    Validates the JWT token from the Authorization header.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Authorization header is required"}), 401

        # Extract token from "Bearer <token>" format
        try:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        except IndexError:
            return jsonify({"error": "Invalid authorization header format"}), 401

        try:
            # Verify the JWT token with Supabase
            user_response = supabase.auth.get_user(token)
            request.user = user_response.user
            request.auth_token = token
        except Exception as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 401

        return await f(*args, **kwargs)

    return decorated_function


async def get_user_context(user_id: str) -> Optional[str]:
    """
    Fetch user context from Supabase.

    Args:
        user_id: The user's UUID

    Returns:
        User context string or None if not found
    """
    try:
        # Fetch user context from the profiles table
        response = supabase.table("profiles").select("context").eq("id", user_id).single().execute()

        if response.data:
            return response.data.get("context", "")
        return None
    except Exception as e:
        print(f"Error fetching user context: {e}")
        return None


@traceable
async def generate_random_phrase(words: list[str], user_context: str) -> PhraseOutput:
    """
    Generate a random phrase using the RandomPhraseCrew.

    Args:
        words: List of words to use in the phrase
        user_context: User context to personalize the phrase

    Returns:
        PhraseOutput with phrase and words used
    """
    inputs = {
        'words': jsonify(words).get_data(as_text=True),
        'user_context': jsonify(user_context).get_data(as_text=True)
    }

    result = await RandomPhraseCrew().crew().kickoff_async(inputs=inputs)

    # CrewAI returns a result with a .pydantic attribute containing the Pydantic model
    if hasattr(result, 'pydantic'):
        return result.pydantic

    # Fallback - return a basic PhraseOutput
    return PhraseOutput(phrase=str(result), words=words)


@traceable
async def get_similar_words(word1: str, word2: str) -> SimilarWordsOutput:
    """
    Suggest related words for a word pair using SimilarWordsCrew.

    Args:
        word1: First word of the pair
        word2: Second word of the pair

    Returns:
        SimilarWordsOutput with list of related words
    """
    inputs = {"word1": word1, "word2": word2}
    result = await SimilarWordsCrew().crew().kickoff_async(inputs=inputs)
    if hasattr(result, "pydantic"):
        return result.pydantic
    return SimilarWordsOutput(similar_words=[str(result)])


def _create_user_supabase(access_token: str) -> Client:
    """Create a Supabase client with the user's JWT for RLS."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.auth.set_session(access_token=access_token, refresh_token="")
    return client


# Phrases that mean "yes, save the word we just discussed"
_SAVE_CONFIRMATION_PHRASES = frozenset(
    p.strip().lower()
    for p in (
        "yes", "yeah", "yep", "sure", "ok", "okay", "please", "please do",
        "save it", "yes, save it", "yes save it", "add it", "add it please",
        "go ahead", "do it", "yes please", "sure thing",
    )
)


def _strip_offer_when_already_in_deck(content: str) -> str:
    """
    If content contains both an offer to save and 'already in your deck',
    remove the offer sentence so we do not say 'Would you like to save? ... already in your deck.'
    """
    if not content or "already in your deck" not in content:
        return content
    # Remove common offer phrases when duplicate message is present
    for phrase in (
        "Would you like me to save this word to your flashcard deck?",
        "Would you like me to add this to your flashcard deck?",
        "Would you like me to add this word to your flashcard deck?",
    ):
        if phrase in content:
            content = content.replace(phrase, "").strip()
            # Collapse multiple spaces and fix ".." or ". ."
            while "  " in content:
                content = content.replace("  ", " ")
            if content.startswith(". "):
                content = content[2:].strip()
    return content


def _extract_save_tool_message_only(content: str) -> str:
    """Keep only the save_word_pair tool result in content; strip any preceding explanation."""
    if not content or not content.strip():
        return content
    # Success message: "Done! I've added ... You'll see it in your next practice session."
    if "Done! I've added" in content:
        start = content.find("Done! I've added")
        end_phrase = "You'll see it in your next practice session."
        end = content.find(end_phrase, start)
        if end != -1:
            return content[start : end + len(end_phrase)].strip()
        return content[start:].strip()
    # Duplicate message: "This word pair (...) is already in your deck. No duplicate was created."
    if "already in your deck" in content or "No duplicate was created" in content:
        start = content.find("This word pair")
        if start != -1:
            end_phrase = "No duplicate was created."
            end = content.find(end_phrase, start)
            if end != -1:
                return content[start : end + len(end_phrase)].strip()
            return content[start:].strip()
    return content


def _detect_save_confirmation_and_override_intent(
    messages: list[dict[str, str]],
) -> Optional[str]:
    """
    If the last user message is a short confirmation and the previous assistant
    offered to save a word to the flashcard deck, return the intent we should
    use instead of the Router (translation or new_vocabulary). Otherwise return None.
    """
    if not messages or len(messages) < 2:
        return None
    last = messages[-1]
    if last.get("role") != "user":
        return None
    user_content = (last.get("content") or "").strip().lower().rstrip(".,!?")
    if not user_content or len(user_content) > 60:
        return None
    if user_content not in _SAVE_CONFIRMATION_PHRASES and not (
        any(w in user_content for w in ("yes", "save", "add", "sure", "please"))
        and len(user_content) <= 25
    ):
        return None
    # Find last assistant message
    last_assistant_content = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "assistant":
            last_assistant_content = (messages[i].get("content") or "").strip().lower()
            break
    if not last_assistant_content:
        return None
    if "flashcard" not in last_assistant_content:
        return None
    if "save" not in last_assistant_content and "add" not in last_assistant_content:
        return None
    # Prefer new_vocabulary if the assistant was clearly suggesting a new word
    if "new word" in last_assistant_content or "vocabulary" in last_assistant_content:
        return "new_vocabulary"
    # Default: treat as confirmation after a translation
    return "translation"


@traceable
async def run_tutor_router(
    messages: list[dict[str, str]],
    user_context: Optional[str] = None,
    user_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    """
    Run the Smart Tutor: Router classifies intent, then delegates to specialist agents.

    Args:
        messages: Full conversation history as a list of {role, content} dicts.
        user_context: Optional user profile/context string.
        user_id: Optional user UUID for save_word_pair tool.
        access_token: Optional JWT for user-scoped Supabase (RLS).

    Returns:
        A dict representation of the TutorMessage pydantic output.
    """
    base_inputs: dict = {"messages": messages}
    if user_context is not None:
        base_inputs["user_context"] = user_context
    else:
        base_inputs["user_context"] = ""

    save_tool = None
    check_tool = None
    if user_id and access_token:
        supabase_user = _create_user_supabase(access_token)
        save_tool = SaveWordPairTool(user_id=user_id, supabase_client=supabase_user)
        check_tool = CheckWordPairInDeckTool(user_id=user_id, supabase_client=supabase_user)

    # Step 1: Router classifies intent
    router_result = await RouterCrew().crew().kickoff_async(inputs=base_inputs)
    if not hasattr(router_result, "pydantic"):
        return {
            "role": "assistant",
            "content": str(router_result),
            "intent": "off_topic",
            "word_card": None,
            "actions": [],
            "delegated_agent": None,
        }
    decision: RouterDecision = router_result.pydantic

    # Override: if user said "yes"/"save it" after an offer to save, force translation/new_vocabulary
    # so the agent that has save_word_pair runs (Router often sends this to Language Tutor otherwise)
    override_intent = _detect_save_confirmation_and_override_intent(messages)
    if (
        override_intent
        and decision.allowed_domain
        and decision.intent not in ("translation", "new_vocabulary")
    ):
        decision = decision.model_copy(
            update={
                "intent": override_intent,
                "specialist_instruction": (
                    "The user confirmed they want to save the word. You MUST call the save_word_pair "
                    "tool with the source word and translation from the conversation (e.g. hello and hola). "
                    "Your response must be EXACTLY the tool's return message and nothing else: "
                    "if the tool says 'Done! I've added...' then output only that; "
                    "if the tool says 'This word pair ... is already in your deck' then output only that. "
                    "Do NOT repeat the translation, pronunciation, or any other explanation."
                ),
            }
        )

    # Step 2: Off-topic -> refuse
    if not decision.allowed_domain:
        refusal = decision.refusal_message or (
            "I'm your language tutor and can only help with language-related questions. "
            "Try asking about translations, vocabulary, grammar, or cultural context!"
        )
        return TutorMessage(
            role="assistant",
            content=refusal,
            intent="off_topic",
            word_card=None,
            actions=[],
            delegated_agent=None,
        ).model_dump()

    # Step 3: Delegate to specialist
    specialist_inputs = {**base_inputs, "specialist_instruction": decision.specialist_instruction}
    is_save_confirmation = "MUST call the save_word_pair" in (decision.specialist_instruction or "")

    if decision.intent == "translation":
        trans_crew = TranslationCrew(save_tool=save_tool, check_tool=check_tool)
        trans_result = await trans_crew.crew().kickoff_async(inputs=specialist_inputs)
        if hasattr(trans_result, "pydantic"):
            content = trans_result.pydantic.content
        else:
            content = str(trans_result)
        if is_save_confirmation and content:
            content = _extract_save_tool_message_only(content)
        else:
            content = _strip_offer_when_already_in_deck(content or "")
        return TutorMessage(
            role="assistant",
            content=content or "",
            intent="translation",
            word_card=None,
            actions=[],
            delegated_agent="Translation Agent",
        ).model_dump()

    if decision.intent == "new_vocabulary":
        vocab_crew = VocabularyCrew(save_tool=save_tool, check_tool=check_tool)
        vocab_result = await vocab_crew.crew().kickoff_async(inputs=specialist_inputs)
        if hasattr(vocab_result, "pydantic"):
            msg = vocab_result.pydantic.model_copy(update={"delegated_agent": "Vocabulary Agent"})
            out = msg.model_dump()
            if is_save_confirmation:
                if out.get("content"):
                    out["content"] = _extract_save_tool_message_only(out["content"])
                out["word_card"] = None
            else:
                if out.get("content"):
                    out["content"] = _strip_offer_when_already_in_deck(out["content"])
            return out
        content = str(vocab_result)
        if is_save_confirmation:
            content = _extract_save_tool_message_only(content)
        return TutorMessage(
            role="assistant",
            content=content,
            intent="new_vocabulary",
            word_card=None,
            actions=[],
            delegated_agent="Vocabulary Agent",
        ).model_dump()

    # Grammar, writing, cultural, small_talk -> Generic Tutor
    generic_result = await GenericTutorCrew().crew().kickoff_async(inputs=specialist_inputs)
    if hasattr(generic_result, "pydantic"):
        msg = generic_result.pydantic.model_copy(update={"delegated_agent": "Language Tutor"})
        return msg.model_dump()
    return TutorMessage(
        role="assistant",
        content=str(generic_result),
        intent=decision.intent,
        word_card=None,
        actions=[],
        delegated_agent="Language Tutor",
    ).model_dump()


@app.route("/health", methods=["GET"])
async def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/api/random-phrase", methods=["POST"])
@require_auth
async def get_random_phrase():
    """
    Generate a random phrase based on provided words and user context.

    Request body:
        {
            "words": ["word1", "word2", ...]
        }

    Headers:
        Authorization: Bearer <jwt_token>

    Response:
        {
            "phrase": "generated phrase",
            "words_used": ["word1", "word2"]
        }
    """
    try:
        # Get words from request body
        data = request.get_json()

        if not data or "words" not in data:
            return jsonify({"error": "Request body must include 'words' array"}), 400

        words = data.get("words", [])

        if not isinstance(words, list) or len(words) == 0:
            return jsonify({"error": "'words' must be a non-empty array"}), 400

        # Get user context from Supabase
        user_id = request.user.id
        user_context = await get_user_context(user_id)

        # Generate the phrase
        result = await generate_random_phrase(words, user_context or "")

        return jsonify(result.model_dump()), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/livekit-token", methods=["POST"])
@require_auth
async def get_livekit_token():
    """
    Issue a LiveKit access token for the current user so the frontend
    can join a voice room with the voice agent.

    Request body (optional):
        {
          "roomName": "string"  // if omitted, a default per-user room is used
        }

    Response:
        {
          "token": "<jwt>",
          "url": "<livekit_server_url>",
          "roomName": "<room_name>"
        }
    """
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        return (
            jsonify(
                {
                    "error": "LiveKit is not configured. Please set LIVEKIT_URL, "
                    "LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in ai/.env.",
                }
            ),
            500,
        )

    try:
        data = request.get_json(silent=True) or {}
        user = request.user
        user_id = str(user.id)

        room_name = (data.get("roomName") or "").strip() or f"wordpan-voice-{user_id}"

        at = lk_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        grants = lk_api.VideoGrants(
            room=room_name,
            room_join=True,
            can_publish=True,
            can_subscribe=True,
        )
        token = at.with_identity(user_id).with_grants(grants).to_jwt()

        # After creating the participant token, explicitly dispatch the agent
        if LIVEKIT_AGENT_NAME:
            try:
                api_client = lk_api.LiveKitAPI()  
                await api_client.agent_dispatch.create_dispatch(
                    lk_api.CreateAgentDispatchRequest(
                        agent_name=LIVEKIT_AGENT_NAME,
                        room=room_name,
                    )
                )
            except Exception as dispatch_err:
                print(f"Failed to dispatch agent: {dispatch_err}", flush=True)

        return jsonify({"token": token, "url": LIVEKIT_URL, "roomName": room_name}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to create LiveKit token: {str(e)}"}), 500


@app.route("/api/similar-words", methods=["POST"])
@require_auth
async def similar_words():
    """
    Suggest related words for a word pair.

    Request body:
        {
            "word1": "string",
            "word2": "string"
        }

    Headers:
        Authorization: Bearer <jwt_token>

    Response:
        {
            "similar_words": ["word1", "word2", ...]
        }
    """
    try:
        data = request.get_json()
        if not data or "word1" not in data or "word2" not in data:
            return (
                jsonify({"error": "Request body must include 'word1' and 'word2'"}), 400
            )
        word1 = (data.get("word1") or "").strip()
        word2 = (data.get("word2") or "").strip()
        if not word1 or not word2:
            return jsonify({"error": "'word1' and 'word2' must be non-empty"}), 400

        result = await get_similar_words(word1, word2)
        return jsonify(result.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/tutor-chat", methods=["POST"])
@require_auth
async def tutor_chat():
    """
    Smart Tutor chat endpoint.

    Request body:
        {
            "messages": [
                {"role": "user" | "assistant" | "system", "content": "text"},
                ...
            ]
        }

    Headers:
        Authorization: Bearer <jwt_token>

    Response:
        TutorMessage dict:
        {
          "role": "assistant",
          "content": "...",
          "intent": "...",
          "word_card": { ... } | null,
          "actions": [ ... ]
        }
    """
    try:
        data = request.get_json()
        if not data or "messages" not in data:
            return jsonify({"error": "Request body must include 'messages' array"}), 400

        messages = data.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({"error": "'messages' must be a non-empty array"}), 400

        # Basic validation of message structure
        validated_messages: list[dict[str, str]] = []
        for msg in messages:
            role = (msg.get("role") or "").strip()
            content = (msg.get("content") or "").strip()
            if role not in {"user", "assistant", "system"} or not content:
                continue
            validated_messages.append({"role": role, "content": content})

        if not validated_messages:
            return jsonify({"error": "No valid messages provided"}), 400

        # Get user context from Supabase (optional, same as random-phrase)
        user_id = str(request.user.id)
        user_context = await get_user_context(user_id)
        access_token = getattr(request, "auth_token", None)

        result = await run_tutor_router(
            validated_messages,
            user_context or "",
            user_id=user_id,
            access_token=access_token,
        )
        return jsonify(result), 200
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, flush=True)
        return (
            jsonify({
                "error": str(e),
                "traceback": tb,
            }),
            500,
        )


if __name__ == "__main__":
    # Run the Flask app
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
