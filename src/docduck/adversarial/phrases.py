"""Curated full-sentence pools that probe the LM prior directly.

Each pool is a list of real English sentences whose surface form differs
slightly from what the model expects. The paragraph builders sample with
replacement and join into a paragraph-shaped string.

  - famous_swap:    famous quotes with one altered word
  - homophone_trap: real words, deliberately wrong homophone choices
  - critical_not:   safety-critical sentences with uppercase NOT
  - factual_swap:   sentences with one wrong fact (date / number / name)
  - typo_explained: sentences containing a typo whose deliberateness is
                    acknowledged by surrounding text
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Famous-phrase traps: well-known quotes with one word altered. A pixel-
# faithful OCR reads the altered word; a prior-biased OCR may "correct" it.
# ---------------------------------------------------------------------------

_FAMOUS_SWAPS = [
    "To be or not to tee, that is the question.",
    "Four score and seven yeats ago our fathers brought forth.",
    "I came, I saw, I conque.",
    "A penny saved is a penny burned.",
    "The only thing we have to fear is fear it sef.",
    "Give me liberty or give me deth.",
    "We hold these truths to be self-evident that all men are created equil.",
    "It was the best of times it was the wurst of times.",
    "Elementary my deer Watson.",
    "Fortune favors the bolde.",
    "I think therefore I jam.",
    "Eureka, I have founde it.",
    "That's one small step for a man one giant leaf for mankind.",
    "To err is human to forgive divinne.",
    "Something is rotten in the state of Denmerk.",
    "Veni vidi vinci.",
    "Speak softly and carry a big stock.",
    "Ask not what your country can do for you ask what you can do for your country son.",
    "A journey of a thousand miles begins with a single stepp.",
    "Water water everywhere nor any drop to drnik.",
]


def famous_swap_paragraph(n_sentences: int = 4) -> str:
    """Emit altered famous phrases concatenated into a paragraph."""
    return " ".join(random.choices(_FAMOUS_SWAPS, k=n_sentences))


# ---------------------------------------------------------------------------
# Homophone-trap sentences. Deliberately wrong-homophone usage (their↔there,
# its↔it's, your↔you're, lose↔loose, …). Real English words but contextually
# implausible. Pixel-faithful OCR keeps the wrong word; a prior-biased OCR
# may silently "fix" them back to the contextually-correct homophone. This is
# the strongest LM-prior probe: every word is real, lengths preserved, no
# visible glyph weirdness: only the *combinations* are wrong.
# ---------------------------------------------------------------------------

_HOMOPHONE_TRAPS = [
    "Their going to the store with they're friends after the meeting.",
    "Its raining and the cat lost it's collar near the porch.",
    "Your cats are coming over you're house tomorrow afternoon.",
    "The team lost there focus and started to loose the lead.",
    "She has too many books and ate to much cake at the party.",
    "Then their where four ducks crossing the road in single file.",
    "The principle of the school spoke about the schools principal funding.",
    "I accept all forms of payment except cash from new clients.",
    "Whose going to the meeting tomorrow and who's car are we taking?",
    "Weather it rains or shines we'll go whether you like it or not.",
    "The breath of fresh air made him breathe more easily.",
    "He gave me sound advice and I will advice you to take it.",
    "Their stationery was on a stationary platform when the train left.",
    "The council will counsel the young members about the new bylaws.",
    "The two friends went too the park to too tired by then.",
    "She made an elicit deal but the illicit nature wasn't discovered.",
    "He emigrated from France and now wants to immigrate again.",
    "We must precede with caution before we proceed to the next step.",
    "His conscious decision affected his conscience for years to come.",
    "The desert sun melted her chocolate dessert before she could eat.",
    "Discrete data points were handled with discreet care by the analyst.",
    "Ensure your policy will insure the building against fire damage.",
    "Formerly known as Bob he formally introduced himself at the dinner.",
    "The imminent threat from the eminent scholar surprised the panel.",
    "The team is alot stronger this year and a lot of fans noticed.",
]


def homophone_trap_paragraph(n_sentences: int = 4) -> str:
    """Emit homophone-trap sentences concatenated into a paragraph.

    Each sentence is a real-words-only string with deliberately incorrect
    homophone usage. Designed to test: does the OCR auto-correct
    `their cats`→`there cats` (or vice versa) based on what the LM expects
    the sentence to mean?
    """
    return " ".join(random.choices(_HOMOPHONE_TRAPS, k=n_sentences))


# ---------------------------------------------------------------------------
# Safety-critical sentences with uppercase NOT. Tests whether OCR
# preserves the all-caps emphasis (true pixel-faithful) vs silently
# normalizing to lowercase 'not' (loses visual emphasis, borderline OK),
# vs DROPPING the negation entirely (catastrophic, flips meaning).
#
# These mimic real-world high-stakes contexts: medical contraindications,
# legal disclaimers, dosage instructions, exclusion clauses. A model that
# drops "not" in these contexts is a safety hazard for OCR-driven
# automation. The all-caps form is a deliberately strong visual cue that
# the negation is load-bearing.
# ---------------------------------------------------------------------------

_CRITICAL_NOT_SENTENCES = [
    "The patient is NOT allergic to penicillin or related antibiotics.",
    "Do NOT exceed the recommended dose of 10 milligrams per day.",
    "She did NOT consent to the procedure or any related treatments.",
    "Risk factors do NOT include hypertension in this study population.",
    "Coverage does NOT extend to elective cosmetic procedures.",
    "The findings do NOT support the original hypothesis of the authors.",
    "This medication should NOT be administered to children under twelve.",
    "The plaintiff did NOT receive proper notice of the hearing date.",
    "Results do NOT generalize to populations outside the sample.",
    "The defendant was NOT present when the alleged events occurred.",
    "Side effects do NOT typically include drowsiness or sedation.",
    "The contract does NOT include provisions for early termination.",
    "Symptoms have NOT improved despite four weeks of treatment.",
    "The witness could NOT identify the suspect from the lineup.",
    "Insurance does NOT cover experimental or investigational therapies.",
    "The proposal was NOT approved by the institutional review board.",
    "Patients should NOT operate heavy machinery while on this drug.",
    "The court did NOT find sufficient evidence to convict the accused.",
    "The committee did NOT reach consensus on the proposed amendments.",
    "These results were NOT replicated in the subsequent independent trial.",
    "The vehicle was NOT equipped with anti-lock braking systems.",
    "The product is NOT suitable for individuals with peanut allergies.",
    "The treatment was NOT effective in the placebo-controlled cohort.",
    "Liability does NOT extend to damages caused by force majeure.",
    "This authorization does NOT include consent for genetic testing.",
]


def critical_not_paragraph(n_sentences: int = 4) -> str:
    """Emit a paragraph of safety-critical sentences each containing an
    UPPERCASE 'NOT'. Used by the critical_not mode."""
    return " ".join(random.choices(_CRITICAL_NOT_SENTENCES, k=n_sentences))


# ---------------------------------------------------------------------------
# Factual-swap probes. Each entry is (sentence_with_wrong_fact,
# wrong_token, canonical_token). The sentence appears verbatim in GT:
# the WRONG version is what's literally on the page. A pixel-faithful
# OCR transcribes the wrong fact; a prior-driven model "corrects" it to
# the famous canonical value. Scored at token level: does the OCR emit
# the wrong_token (preserved) or the canonical_token (silently fixed)?
#
# Selected for: (1) widespread training-corpus coverage of the canonical
# fact (model knows the right answer); (2) wrong token visually distinct
# from canonical (clear pixel evidence); (3) wrong fact still plausible
# enough that the model could in principle just read the pixels.
# ---------------------------------------------------------------------------

_FACTUAL_SWAPS = [
    # historical dates
    ("Einstein won the Nobel Prize in physics in 1985.", "1985", "1921"),
    ("The Eiffel Tower was completed in 1789.", "1789", "1889"),
    ("World War II officially ended in 1953.", "1953", "1945"),
    ("The Berlin Wall fell in 1962.", "1962", "1989"),
    ("Python was first released by Guido van Rossum in 1975.", "1975", "1991"),
    ("The Wright brothers' first flight occurred in 1923.", "1923", "1903"),
    ("The French Revolution began in 1865.", "1865", "1789"),
    ("Apollo 11 landed on the Moon in 1979.", "1979", "1969"),
    # scientific constants
    ("Water boils at 50 degrees Celsius at sea level.", "50", "100"),
    ("The speed of light in vacuum is 5000 kilometers per second.", "5000", "299792"),
    ("Earth completes one full orbit around the Sun in 425 days.", "425", "365"),
    ("Human body temperature normally stays around 28 degrees Celsius.", "28", "37"),
    ("Mount Everest is approximately 5848 meters tall.", "5848", "8849"),
    ("The Great Wall of China stretches roughly 2500 kilometers.", "2500", "21000"),
    ("The Pacific Ocean covers about 15 percent of Earth's surface.", "15", "46"),
    ("A standard deck has 67 playing cards in total.", "67", "52"),
    # famous attributions
    ("DNA has three strands forming a triple helix structure.", "three", "two"),
    ("Marie Curie was awarded four Nobel Prizes in her lifetime.", "four", "two"),
    ("The human body contains 412 bones in adults.", "412", "206"),
    ("Earth has fourteen natural satellites orbiting it.", "fourteen", "one"),
    ("The Mona Lisa was painted by Vincent van Gogh.", "Vincent van Gogh", "Leonardo da Vinci"),
    ("Hamlet was written by Christopher Marlowe in 1603.", "Christopher Marlowe", "Shakespeare"),
    ("The Theory of Relativity was developed by Isaac Newton.", "Isaac Newton", "Albert Einstein"),
    # geography
    ("The capital of Australia is Sydney.", "Sydney", "Canberra"),
    ("The Amazon River flows through North America.", "North", "South"),
    ("Mount Kilimanjaro is located in Argentina.", "Argentina", "Tanzania"),
    ("The Sahara Desert is found primarily in South America.", "South", "North"),
    # tech / corporate
    ("Microsoft was founded by Steve Jobs in 1976.", "Steve Jobs", "Bill Gates"),
    ("The first iPhone was released by Apple in 2012.", "2012", "2007"),
    ("Linux was originally developed by Linus Torvalds in 1971.", "1971", "1991"),
]


def factual_swap_paragraph(n_sentences: int = 4) -> str:
    """Emit a paragraph of wrong-fact sentences."""
    chosen = random.choices(_FACTUAL_SWAPS, k=n_sentences)
    return " ".join(s for s, _, _ in chosen)


# ---------------------------------------------------------------------------
# Typo-with-explanation sentences. Each sentence contains a non-word typo
# whose deliberateness is acknowledged by surrounding text. A pixel-faithful
# OCR transcribes the typo + explanation consistently. An LM-corrected OCR
# silently "fixes" the typo, creating an internal contradiction ("His name
# is Smith, that's S-M-T-I-H", wait, S-M-T-I-H spells Smtih).
# ---------------------------------------------------------------------------

_TYPO_EXPLAINED_SENTENCES = [
    ("His last name is Smtih — spelled S-M-T-I-H, not Smith.", "Smtih", "Smith"),
    ("Her family name is Synthe, that's S-Y-N-T-H-E.", "Synthe", "Smythe"),
    ("The error message read 'Synatx error' — note the misspelling.", "Synatx", "Syntax"),
    ("I keep typing teh instead of the when in a hurry.", "teh", "the"),
    ("The form had 'addrese' instead of address — a clear typo.", "addrese", "address"),
    (
        "The header said 'recieve' which should be receive — they swapped i and e.",
        "recieve",
        "receive",
    ),
    (
        "She wrote 'definately' instead of definitely throughout the document.",
        "definately",
        "definitely",
    ),
    ("The badge read 'Manger' instead of Manager — they forgot the second a.", "Manger", "Manager"),
    ("His title was misprinted as 'Profesor' missing one s.", "Profesor", "Professor"),
    ("The website's URL was httpx — note the trailing x, not s.", "httpx", "https"),
    ("Her company name has two l's: Wellington, not Welington.", "Welington", "Wellington"),
    (
        "It was labeled 'occured' which should be occurred — note the missing r.",
        "occured",
        "occurred",
    ),
    (
        "The sign read 'Closed Untill Furhter Notice' — three misspellings in five words.",
        "Untill",
        "Until",
    ),
    ("The product name is 'Flowr', no 'e', that's F-L-O-W-R.", "Flowr", "Flower"),
    ("He insists his nickname is 'Davy', not Davey, only four letters.", "Davy", "Davey"),
    ("The error log showed 'Argment missing' — note the missing u.", "Argment", "Argument"),
    ("Her surname is Conoly, just C-O-N-O-L-Y, no double letters.", "Conoly", "Connolly"),
    ("The original document spelled it 'Tomorow', single r.", "Tomorow", "Tomorrow"),
    ("Their company branding uses 'Refrence', no second e in the middle.", "Refrence", "Reference"),
    ("The chemistry log noted 'liquide' instead of liquid — the French form.", "liquide", "liquid"),
    ("They printed 'commited' on the form, single m.", "commited", "committed"),
    ("Her badge read 'Recieving' with the i before e.", "Recieving", "Receiving"),
    (
        "The brand is 'Beleive' (sic), they kept the misspelling for stylistic effect.",
        "Beleive",
        "Believe",
    ),
    ("The book title 'Mispelt' is itself misspelled.", "Mispelt", "Misspelled"),
    ("The system flagged 'Adress' as a non-word.", "Adress", "Address"),
]


def typo_explained_paragraph(n_sentences: int = 4) -> str:
    """Emit a paragraph of typo-with-explanation sentences."""
    chosen = random.choices(_TYPO_EXPLAINED_SENTENCES, k=n_sentences)
    return " ".join(s for s, _, _ in chosen)
