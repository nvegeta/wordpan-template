from pydantic import BaseModel, Field
from typing import List


class SimilarWordsOutput(BaseModel):
    """Schema for similar/related words suggestion output."""

    similar_words: List[str] = Field(
        ...,
        description="List of words related to the given word pair (synonyms, related terms, or words that pair well)",
        min_length=1,
        max_length=12,
    )
