"""Tool to check if a word pair is already in the user's flashcard deck."""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from supabase import Client


class CheckWordPairInput(BaseModel):
    """Input schema for CheckWordPairInDeckTool."""

    source_word: str = Field(
        ...,
        description="The word in the user's native language",
    )
    translated_word: str = Field(
        ...,
        description="The translation in the target language",
    )


class CheckWordPairInDeckTool(BaseTool):
    """
    Check whether a word pair is already in the user's flashcard deck.
    Call this when you are about to offer to save a word, so you can skip the offer
    and instead say it's already in the deck if it is.
    """

    name: str = "check_word_pair_in_deck"
    description: str = (
        "Check if a word pair is already in the user's flashcard deck. "
        "Call this BEFORE offering to save, when you have just given a translation or new word. "
        "If the result is 'already in deck', do NOT offer to save; say the pair is already in the deck. "
        "If the result is 'not in deck', then offer to save."
    )
    args_schema: Type[BaseModel] = CheckWordPairInput

    def __init__(self, user_id: str, supabase_client: Client, **kwargs):
        super().__init__(**kwargs)
        self._user_id = user_id
        self._supabase = supabase_client

    def _run(self, source_word: str, translated_word: str) -> str:
        """Return whether the pair is already in the user's deck."""
        source = (source_word or "").strip()
        translated = (translated_word or "").strip()
        if not source or not translated:
            return "not in deck"
        try:
            existing = (
                self._supabase.table("word_pairs")
                .select("id", "word1", "word2")
                .eq("user_id", self._user_id)
                .execute()
            )
            if existing.data:
                sl = source.lower()
                tl = translated.lower()
                for row in existing.data:
                    if (
                        (row.get("word1") or "").lower() == sl
                        and (row.get("word2") or "").lower() == tl
                    ):
                        return (
                            f"already in deck: This word pair ('{source}' → '{translated}') "
                            "is already in your deck."
                        )
            return "not in deck"
        except Exception:
            return "not in deck"
