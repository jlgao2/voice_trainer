"""Sample passages for voice training practice."""

import random
from dataclasses import dataclass
from typing import List


@dataclass
class Passage:
    """A practice passage with metadata."""
    id: str
    title: str
    text: str
    focus: str  # What aspect of voice this passage targets
    estimated_duration: int  # Approximate seconds to read


PASSAGES: List[Passage] = [
    Passage(
        id="pitch_range_1",
        title="The Question Game",
        text=(
            "Did you see that? I can't believe it actually worked! "
            "Wait, are you serious right now? That's absolutely incredible."
        ),
        focus="pitch_range",
        estimated_duration=8,
    ),
    Passage(
        id="pitch_range_2",
        title="Emotional Contrast",
        text=(
            "The morning started terribly. Everything went wrong. "
            "But then, something magical happened, and suddenly the whole day turned around!"
        ),
        focus="pitch_range",
        estimated_duration=10,
    ),
    Passage(
        id="sustained_1",
        title="Smooth Sailing",
        text=(
            "The ocean waves rolled slowly toward the shore. "
            "Seagulls soared smoothly through the serene summer sky. "
            "The scene was simply sensational."
        ),
        focus="sustained_sounds",
        estimated_duration=12,
    ),
    Passage(
        id="intonation_1",
        title="The List",
        text=(
            "We need apples, oranges, bananas, and grapes from the store. "
            "Also milk, bread, eggs, and cheese. Oh, and don't forget the coffee!"
        ),
        focus="intonation_patterns",
        estimated_duration=10,
    ),
    Passage(
        id="intonation_2",
        title="Directions",
        text=(
            "First, turn left at the corner. Then, go straight for two blocks. "
            "Finally, you'll see it on your right. You really can't miss it."
        ),
        focus="intonation_patterns",
        estimated_duration=10,
    ),
    Passage(
        id="volume_1",
        title="The Secret",
        text=(
            "Come closer, I have something important to tell you. "
            "This is absolutely crucial, so listen carefully. "
            "Now, here's what you need to know."
        ),
        focus="volume_control",
        estimated_duration=10,
    ),
    Passage(
        id="pacing_1",
        title="Rapid Fire",
        text=(
            "Peter Piper picked a peck of pickled peppers. "
            "She sells seashells by the seashore. "
            "How much wood would a woodchuck chuck?"
        ),
        focus="articulation_speed",
        estimated_duration=12,
    ),
    Passage(
        id="resonance_1",
        title="Deep Thoughts",
        text=(
            "The mountain stood tall and majestic against the horizon. "
            "Thunder rumbled in the distance, powerful and profound. "
            "The moment demanded respect and reflection."
        ),
        focus="chest_resonance",
        estimated_duration=12,
    ),
    Passage(
        id="brightness_1",
        title="Light and Cheerful",
        text=(
            "The tiny kitten played with a bright yellow ribbon. "
            "It leaped and twirled with delightful energy. "
            "Every little movement was filled with pure joy!"
        ),
        focus="head_voice_brightness",
        estimated_duration=10,
    ),
    Passage(
        id="mixed_1",
        title="The Story",
        text=(
            "Once upon a time, in a land far away, there lived a wise old sage. "
            "He knew the secrets of the universe. 'Would you like to learn them?' he asked. "
            "And so began the greatest adventure of all."
        ),
        focus="mixed_expression",
        estimated_duration=15,
    ),
]


def get_random_passage() -> Passage:
    """Get a random passage for practice."""
    return random.choice(PASSAGES)


def get_passage_by_id(passage_id: str) -> Passage | None:
    """Get a specific passage by ID."""
    for passage in PASSAGES:
        if passage.id == passage_id:
            return passage
    return None


def get_passages_by_focus(focus: str) -> List[Passage]:
    """Get all passages targeting a specific focus area."""
    return [p for p in PASSAGES if p.focus == focus]


def list_all_passages() -> List[Passage]:
    """Get all available passages."""
    return PASSAGES.copy()
