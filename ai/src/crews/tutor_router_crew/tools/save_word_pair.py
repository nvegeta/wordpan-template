"""Tool to save word pairs to the user's flashcard deck."""

from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from supabase import Client


class SaveWordPairInput(BaseModel):
    """Input schema for SaveWordPairTool. required: source_word, translated_word."""

    source_word: str = Field(
        ...,
        description="The word in the user's native language",
    )
    translated_word: str = Field(
        ...,
        description="The translation in the target language",
    )
    context_sentence: Optional[str] = Field(
        default=None,
        description="An example sentence using the word",
    )


class SaveWordPairTool(BaseTool):
    """Save a word and its translation to the user's personal flashcard deck for future practice."""

    name: str = "save_word_pair"
    description: str = (
        "Save a word and its translation to the user's personal flashcard deck for future practice. "
        "Use when the user confirms they want to save (e.g. 'Yes, save it!'). "
        "If the pair already exists, the tool returns a message saying so; tell the user that exactly."
    )
    args_schema: Type[BaseModel] = SaveWordPairInput

    def __init__(self, user_id: str, supabase_client: Client, **kwargs):
        super().__init__(**kwargs)
        self._user_id = user_id
        self._supabase = supabase_client

    def _run(
        self,
        source_word: str,
        translated_word: str,
        context_sentence: Optional[str] = None,
    ) -> str:
        """Save the word pair to the user's deck. Returns confirmation or duplicate message."""
        source = (source_word or "").strip()
        translated = (translated_word or "").strip()
        if not source or not translated:
            return "Cannot save: both source_word and translated_word are required."

        try:
            # Check for duplicate (same user, same word pair; case-insensitive)
            existing = (
                self._supabase.table("word_pairs")
                .select("id", "word1", "word2")
                .eq("user_id", self._user_id)
                .execute()
            )
            if existing.data:
                source_lower = source.lower()
                translated_lower = translated.lower()
                for row in existing.data:
                    if (
                        (row.get("word1") or "").lower() == source_lower
                        and (row.get("word2") or "").lower() == translated_lower
                    ):
                        return (
                            f"This word pair ('{source}' → '{translated}') is already in your deck. "
                            "No duplicate was created."
                        )

            # Insert new word pair
            insert_data = {
                "user_id": self._user_id,
                "word1": source,
                "word2": translated,
            }
            self._supabase.table("word_pairs").insert(insert_data).execute()

            return (
                f"Done! I've added '{source}' → '{translated}' to your flashcard deck. "
                "You'll see it in your next practice session."
            )

        except Exception as e:
            return f"Failed to save the word pair: {str(e)}"
