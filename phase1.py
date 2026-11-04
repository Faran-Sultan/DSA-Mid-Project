"""
CSC200 - DSA | Mid Term Project
Phase 1: Card and Deck
"""

import random

# Constants
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RED_SUITS = {"Hearts", "Diamonds"}          # the other two are black
SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}

# Ranks are stored as numbers 1..13 so comparing them is easy later
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}


class Card:
    """A single playing card."""

    def __init__(self, suit, rank, face_up=False):
        if suit not in SUITS:
            raise ValueError(f"Invalid suit: {suit}")
        if not 1 <= rank <= 13:
            raise ValueError(f"Invalid rank: {rank} (must be 1-13)")
        self.suit = suit
        self.rank = rank          # 1 = Ace ... 11 = Jack, 12 = Queen, 13 = King
        self.face_up = face_up    # cards start face down

    # Properties
    @property
    def color(self):
        """'Red' for Hearts/Diamonds, 'Black' for Clubs/Spades.
        Needed in Phase 3 for the alternating-colors rule."""
        return "Red" if self.suit in RED_SUITS else "Black"

    @property
    def label(self):
        """Rank as shown on the card: A, 2-10, J, Q, K."""
        return RANK_LABELS.get(self.rank, str(self.rank))

    # Actions
    def flip(self):
        """Turn the card over (face up <-> face down)."""
        self.face_up = not self.face_up

    # Display
    def __str__(self):
        if self.face_up:
            return f"{self.label}{SUIT_SYMBOLS[self.suit]}"
        return "[##]"             # face-down card

    def __repr__(self):
        state = "up" if self.face_up else "down"
        return f"Card({self.label} of {self.suit}, {state})"


class Deck:
    """A standard 52-card deck stored in a Python list (array)."""

    def __init__(self):
        self.cards = []
        self.build()

    def build(self):
        """Create all 52 cards: 4 suits x 13 ranks (all face down)."""
        self.cards = [Card(suit, rank) for suit in SUITS for rank in range(1, 14)]

    def shuffle(self):
        """Fisher-Yates shuffle: O(n) time, O(1) extra space, unbiased.

        Walk from the last position down to 1. At each position i, pick a
        random position j in [0, i] and swap cards[i] with cards[j].
        """
        for i in range(len(self.cards) - 1, 0, -1):
            j = random.randint(0, i)
            self.cards[i], self.cards[j] = self.cards[j], self.cards[i]

    def draw(self):
        """Remove and return the top card (end of the list), or None if empty."""
        if self.is_empty():
            return None
        return self.cards.pop()

    def is_empty(self):
        return len(self.cards) == 0

    def __len__(self):
        return len(self.cards)

    def __str__(self):
        return " ".join(str(c) for c in self.cards)



# Quick tests for Phase 1
def run_tests():
    # 1. Card basics
    c = Card("Hearts", 12)
    assert c.color == "Red" and c.label == "Q" and not c.face_up
    c.flip()
    assert c.face_up and str(c) == "Q♥"

    # 2. Invalid cards are rejected
    for bad in (("Stars", 5), ("Spades", 0), ("Spades", 14)):
        try:
            Card(*bad)
            assert False, "should have raised ValueError"
        except ValueError:
            pass

    # 3. Deck has 52 unique cards
    deck = Deck()
    assert len(deck) == 52
    assert len({(x.suit, x.rank) for x in deck.cards}) == 52

    # 4. Shuffle keeps the same 52 cards but changes the order
    before = [(x.suit, x.rank) for x in deck.cards]
    deck.shuffle()
    after = [(x.suit, x.rank) for x in deck.cards]
    assert sorted(before) == sorted(after)     # same cards
    assert before != after                     # different order (practically certain)

    # 5. Drawing removes cards
    top = deck.draw()
    assert isinstance(top, Card) and len(deck) == 51
    while not deck.is_empty():
        deck.draw()
    assert deck.draw() is None

    print("All Phase 1 tests passed!")


if __name__ == "__main__":
    deck = Deck()
    print("Fresh deck (all face down):")
    print(deck, "\n")

    for card in deck.cards:          # show faces for the demo
        card.face_up = True
    print("Fresh deck (face up, ordered):")
    print(deck, "\n")

    deck.shuffle()
    print("After shuffle:")
    print(deck, "\n")

    run_tests()
