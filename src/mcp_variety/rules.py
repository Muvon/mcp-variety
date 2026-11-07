"""Humanisation rules. One list feeds both the checker and the Avoid block of the protocol."""

from dataclasses import dataclass

OPENING_WORDS = 3
MAX_EXCLAMATIONS = 1


@dataclass(frozen=True)
class Rule:
    id: str
    instruction: str


# Phrases that show up far more often in model output than in human writing. The first three double
# as the examples in the Avoid block. All are matched as whole words, so "delve" does not hit "delveloper".
STOCK_PHRASES = (
    "here's the thing",
    "let's dive in",
    "game-changer",
    "game changer",
    "game-changing",
    "in today's fast-paced world",
    "in today's digital age",
    "in the ever-evolving",
    "ever-evolving landscape",
    "ever-changing landscape",
    "it's worth noting",
    "it's important to note",
    "it is important to note",
    "it's no secret that",
    "it goes without saying",
    "needless to say",
    "delve",
    "delves",
    "delving",
    "dive deep",
    "deep dive",
    "unlock the power",
    "unlock the potential",
    "unlock new",
    "harness the power",
    "unleash",
    "elevate your",
    "take it to the next level",
    "supercharge",
    "revolutionize",
    "navigate the landscape",
    "navigate the complexities",
    "a testament to",
    "tapestry",
    "in the realm of",
    "treasure trove",
    "beacon of",
    "myriad of",
    "stay ahead of the curve",
    "at the end of the day",
    "look no further",
    "without further ado",
    "buckle up",
    "let that sink in",
    "in conclusion",
    "embark on a journey",
    "plays a crucial role",
    "plays a pivotal role",
    "seamless",
    "seamlessly",
    "robust",
    "leverage",
    "leveraging",
    "cutting-edge",
    "paradigm shift",
    "holistic approach",
    "moreover",
    "furthermore",
    "foster a sense of",
    "don't hesitate to",
    "feel free to reach out",
    "i hope this email finds you well",
    "i hope this message finds you well",
    "i'm thrilled to announce",
    "i'm excited to share",
    "as an ai language model",
)

_STOCK_EXAMPLES = ", ".join(f'"{phrase}"' for phrase in STOCK_PHRASES[:3])

EM_DASH = Rule("em_dash", "Use no em dashes and no spaced en dashes. Use a period, a comma or a colon instead.")
STOCK_PHRASE = Rule("stock_phrase", f"Skip stock phrases such as {_STOCK_EXAMPLES}. Say the plain thing.")
CONTRAST = Rule(
    "contrast",
    'Do not build sentences like "not just X, but Y" or "it\'s not X, it\'s Y". Say the point once, directly.',
)
UNIFORM_SENTENCES = Rule("uniform_sentences", "Vary the sentence length. Mix very short sentences with longer ones.")
EXCLAMATIONS = Rule("exclamations", f"Use at most {MAX_EXCLAMATIONS} exclamation mark per text.")
REPEATED_OPENING = Rule(
    "repeated_opening",
    f"Do not begin with the same first {OPENING_WORDS} words as your recent texts in this scope.",
)

RULES = (EM_DASH, STOCK_PHRASE, CONTRAST, UNIFORM_SENTENCES, EXCLAMATIONS, REPEATED_OPENING)


def avoid_block() -> str:
    return "\n".join(["Avoid:", *(f"- {rule.instruction}" for rule in RULES)])
