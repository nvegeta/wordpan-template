import asyncio
import os
import traceback
import warnings
from functools import wraps
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
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


@traceable
async def run_tutor_router(
    messages: list[dict[str, str]],
    user_context: Optional[str] = None,
) -> dict:
    """
    Run the Smart Tutor: Router classifies intent, then delegates to specialist agents.

    Args:
        messages: Full conversation history as a list of {role, content} dicts.
        user_context: Optional user profile/context string.

    Returns:
        A dict representation of the TutorMessage pydantic output.
    """
    base_inputs: dict = {"messages": messages}
    if user_context is not None:
        base_inputs["user_context"] = user_context
    else:
        base_inputs["user_context"] = ""

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

    if decision.intent == "translation":
        trans_result = await TranslationCrew().crew().kickoff_async(inputs=specialist_inputs)
        if hasattr(trans_result, "pydantic"):
            content = trans_result.pydantic.content
        else:
            content = str(trans_result)
        return TutorMessage(
            role="assistant",
            content=content,
            intent="translation",
            word_card=None,
            actions=[],
            delegated_agent="Translation Agent",
        ).model_dump()

    if decision.intent == "new_vocabulary":
        vocab_result = await VocabularyCrew().crew().kickoff_async(inputs=specialist_inputs)
        if hasattr(vocab_result, "pydantic"):
            msg = vocab_result.pydantic.model_copy(update={"delegated_agent": "Vocabulary Agent"})
            return msg.model_dump()
        return TutorMessage(
            role="assistant",
            content=str(vocab_result),
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
        user_id = request.user.id
        user_context = await get_user_context(user_id)

        result = await run_tutor_router(validated_messages, user_context or "")
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
