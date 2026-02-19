from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WordCard(BaseModel):
    """Structured vocabulary card for the Smart Tutor."""

    word: str = Field(..., description="The target language word the student should learn")
    translation: str = Field(..., description="Translation of the word in the learner's native language")
    example_sentence: str = Field(..., description="An example sentence using the word in context")
    explanation: Optional[str] = Field(
        None, description="Optional explanation of usage, nuance, or grammar"
    )
    part_of_speech: Optional[str] = Field(
        None, description="Part of speech (e.g., noun, verb, adjective)"
    )


IntentType = Literal[
    "translation",
    "new_vocabulary",
    "grammar_explanation",
    "writing_correction",
    "cultural_context",
    "small_talk_language_related",
    "off_topic",
]


class RouterDecision(BaseModel):
    """Internal routing decision used by the tutor router."""

    intent: IntentType = Field(
        ...,
        description="Detected intent of the user's request",
    )
    allowed_domain: bool = Field(
        ...,
        description="Whether the request is within the allowed language-learning domain",
    )
    specialist_instruction: str = Field(
        ...,
        description="Short instruction for the specialist agent on how to handle this request",
    )
    refusal_message: Optional[str] = Field(
        None,
        description="If allowed_domain is false, a polite refusal message explaining the limitation",
    )


class TutorAction(BaseModel):
    """Optional actions the tutor suggests, such as saving a word to flashcards."""

    type: str = Field(
        ...,
        description=(
            "Type of action to perform in the application. "
            "Recommended values include 'add_to_flashcards' or 'suggest_rephrase'."
        ),
    )
    payload: dict = Field(
        default_factory=dict,
        description="Arbitrary payload describing the action (e.g., word details)",
    )


class TranslationOutput(BaseModel):
    """Output from the Translation Agent."""

    content: str = Field(
        ...,
        description="Translation with explanation and example usage",
    )


class TutorMessage(BaseModel):
    """Final structured output returned by the Smart Tutor router."""

    role: Literal["assistant"] = Field(
        "assistant",
        description="The role of the sender in the conversation (always assistant for tutor outputs)",
    )
    content: str = Field(
        ...,
        description="Natural language reply to show in the chat UI",
    )
    intent: IntentType = Field(
        ...,
        description="Detected intent of the user's request",
    )
    word_card: Optional[WordCard] = Field(
        None,
        description="Optional vocabulary card to render in a special format in the UI",
    )
    actions: List[TutorAction] = Field(
        default_factory=list,
        description="Optional list of actions the frontend/backend can execute",
    )
    delegated_agent: Optional[str] = Field(
        None,
        description="Which specialist agent handled this (e.g. 'Translation Agent', 'Vocabulary Agent') for UI display",
    )

