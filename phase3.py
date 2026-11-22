"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Phase 3: Game Logic  (+ bonus: undo/redo, hints, timer & scoring)

The Game class ties everything together:

    Array/List  -> the 52-card Deck (phase1) before dealing
    Queue       -> self.stock       (draw pile, FIFO)
    Stack       -> self.waste, and the 4 foundation piles (LIFO)
    Linked list -> self.tableau     (7 columns, phase2.TableauPile)
    Dictionary  -> self.positions   (card -> where it is right now)
                   self.foundation  (suit -> foundation pile)
    Stacks      -> self.undo_stack / self.redo_stack (history of moves)

Columns are 0-based inside this module (column 0 = the first column).
The text interface (phase4) converts to the 1-based numbers players see.

Every public move method returns a pair:  (success: bool, message: str)
"""

import random
import time

from phase1 import Deck, SUITS
from phase2 import (Stack, Queue, TableauPile, FoundationPile,
                    move_card, move_run)

NUM_COLUMNS = 7

# Scoring (similar to classic Windows Solitaire)
SCORE_WASTE_TO_TABLEAU = 5
SCORE_TO_FOUNDATION = 10
SCORE_FLIP = 5
SCORE_FOUNDATION_TO_TABLEAU = -15
SCORE_RECYCLE = -50


class Move:
    """A record of one move. Kept on the undo/redo stacks.

    kind is one of:
        DRAW     draw `count` cards from the stock to the waste
        RECYCLE  turn the waste pile back into the stock
        W2T      waste -> tableau column `dst`
        W2F      waste -> foundation pile of suit `dst`
        T2F      tableau column `src` -> foundation pile of suit `dst`
        T2T      `count` cards from column `src` -> column `dst`
        F2T      foundation pile of suit `src` -> tableau column `dst`
    """

    def __init__(self, kind, src=None, dst=None, count=1):
        self.kind = kind
        self.src = src
        self.dst = dst
        self.count = count
        self.flipped = False      # did this move turn a face-down card up?
        self.score_delta = 0      # exact score change (so undo is exact)
        self.cards = None         # RECYCLE: the cards that were turned over


class Game:
    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def __init__(self, draw_count=1, seed=None):
        if draw_count not in (1, 3):
            raise ValueError("draw_count must be 1 or 3")
        self.draw_count = draw_count
        if seed is not None:
            random.seed(seed)          # reproducible deals (handy for testing)
        self._setup()

    def _setup(self):
        deck = Deck()                  # array/list of 52 cards
        deck.shuffle()

        self.stock = Queue()
        self.waste = Stack()
        self.tableau = [TableauPile() for _ in range(NUM_COLUMNS)]
        self.foundation = {suit: FoundationPile(suit) for suit in SUITS}

        # Deal: column i gets i+1 cards, only the last one face up.
        for col in range(NUM_COLUMNS):
            for row in range(col + 1):
                card = deck.draw()
                card.face_up = (row == col)
                self.tableau[col].append(card)

        # The remaining 24 cards form the stockpile (face down).
        while not deck.is_empty():
            self.stock.enqueue(deck.draw())

        self.undo_stack = Stack()
        self.redo_stack = Stack()
        self.score = 0
        self.start_time = time.time()
        self.end_time = None
        self.positions = self._build_positions()

    # ------------------------------------------------------------------
    # Dictionary of card positions
    # ------------------------------------------------------------------
    def _piles(self):
        """Yield (kind, index, list_of_cards) for every pile in the game."""
        yield "stock", 0, self.stock.to_list()
        yield "waste", 0, self.waste.to_list()
        for suit in SUITS:
            yield "foundation", suit, self.foundation[suit].to_list()
        for col in range(NUM_COLUMNS):
            yield "tableau", col, self.tableau[col].to_list()

    def _build_positions(self):
        """card key -> (pile kind, pile index, depth within that pile)"""
        positions = {}
        for kind, idx, cards in self._piles():
            for depth, card in enumerate(cards):
                positions[(card.suit, card.rank)] = (kind, idx, depth)
        return positions

    def _sync(self, *piles):
        """Refresh the dictionary entries of just the piles that changed."""
        for kind, idx in piles:
            if kind == "stock":
                cards = self.stock.to_list()
            elif kind == "waste":
                cards = self.waste.to_list()
            elif kind == "foundation":
                cards = self.foundation[idx].to_list()
            else:
                cards = self.tableau[idx].to_list()
            for depth, card in enumerate(cards):
                self.positions[(card.suit, card.rank)] = (kind, idx, depth)

    def locate(self, card):
        """Where is this card? -> (pile kind, pile index, depth)."""
        return self.positions[(card.suit, card.rank)]

    def check_consistency(self):
        """True if the dictionary matches the piles and all 52 cards exist."""
        rebuilt = self._build_positions()
        return len(rebuilt) == 52 and rebuilt == self.positions

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------
    @staticmethod
    def can_stack_on_tableau(card, pile):
        """Tableau rule: alternating colour and one rank lower;
        only a King may go on an empty column."""
        top = pile.peek()
        if top is None:
            return card.rank == 13
        return (top.face_up and top.color != card.color
                and top.rank == card.rank + 1)

    @staticmethod
    def is_valid_run(cards):
        """Is this sequence (bottom -> top) a legal alternating, descending run?"""
        for lower, upper in zip(cards, cards[1:]):
            if lower.color == upper.color or lower.rank != upper.rank + 1:
                return False
        return True

    @staticmethod
    def _valid_col(col):
        return isinstance(col, int) and 0 <= col < NUM_COLUMNS

    def is_won(self):
        """Won when all four foundation piles hold Ace..King (52 cards)."""
        return all(pile.is_complete() for pile in self.foundation.values())

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------
    def elapsed(self):
        end = self.end_time if self.end_time is not None else time.time()
        return int(end - self.start_time)

    def elapsed_str(self):
        minutes, seconds = divmod(self.elapsed(), 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def move_count(self):
        return len(self.undo_stack)

    # ------------------------------------------------------------------
    # Public moves (validate, then execute)
    # ------------------------------------------------------------------
    def draw(self):
        """Draw 1 or 3 cards from the stock to the waste.
        If the stock is empty, turn the waste pile over to refill it."""
        if not self.stock.is_empty():
            n = min(self.draw_count, len(self.stock))
            return self._execute(Move("DRAW", count=n),
                                 f"Drew {n} card(s) from the stock.")
        if not self.waste.is_empty():
            return self._execute(Move("RECYCLE"),
                                 "Stock was empty - waste pile turned over.")
        return False, "Stock and waste are both empty."

    def move_waste_to_tableau(self, col):
        if not self._valid_col(col):
            return False, "Column must be between 1 and 7."
        card = self.waste.peek()
        if card is None:
            return False, "The waste pile is empty."
        if not self.can_stack_on_tableau(card, self.tableau[col]):
            return False, f"{card} cannot be placed on column {col + 1}."
        return self._execute(Move("W2T", dst=col),
                             f"Moved {card} from the waste to column {col + 1}.")

    def move_waste_to_foundation(self):
        card = self.waste.peek()
        if card is None:
            return False, "The waste pile is empty."
        if not self.foundation[card.suit].can_accept(card):
            return False, f"{card} cannot go to the foundation yet."
        return self._execute(Move("W2F", dst=card.suit),
                             f"Moved {card} from the waste to the foundation.")

    def move_tableau_to_foundation(self, col):
        if not self._valid_col(col):
            return False, "Column must be between 1 and 7."
        card = self.tableau[col].peek()
        if card is None:
            return False, f"Column {col + 1} is empty."
        if not self.foundation[card.suit].can_accept(card):
            return False, f"{card} cannot go to the foundation yet."
        return self._execute(Move("T2F", src=col, dst=card.suit),
                             f"Moved {card} from column {col + 1} to the foundation.")

    def move_tableau_to_tableau(self, src, dst, count=1):
        if not (self._valid_col(src) and self._valid_col(dst)):
            return False, "Columns must be between 1 and 7."
        if src == dst:
            return False, "Source and destination are the same column."
        pile = self.tableau[src]
        if count < 1 or count > len(pile):
            return False, f"Column {src + 1} does not have {count} card(s)."
        run = pile.top_cards(count)
        if not all(card.face_up for card in run):
            return False, "You cannot move face-down cards."
        if not self.is_valid_run(run):
            return False, "Those cards are not an alternating, descending run."
        if not self.can_stack_on_tableau(run[0], self.tableau[dst]):
            return False, f"{run[0]} cannot be placed on column {dst + 1}."
        return self._execute(
            Move("T2T", src=src, dst=dst, count=count),
            f"Moved {count} card(s) from column {src + 1} to column {dst + 1}.")

    def move_foundation_to_tableau(self, suit, col):
        if suit not in SUITS:
            return False, f"Unknown suit: {suit}"
        if not self._valid_col(col):
            return False, "Column must be between 1 and 7."
        card = self.foundation[suit].peek()
        if card is None:
            return False, f"The {suit} foundation is empty."
        if not self.can_stack_on_tableau(card, self.tableau[col]):
            return False, f"{card} cannot be placed on column {col + 1}."
        return self._execute(
            Move("F2T", src=suit, dst=col),
            f"Moved {card} from the foundation to column {col + 1}.")

    def auto_move_to_foundation(self):
        """Keep moving any available top card to the foundation.
        Returns how many cards were moved (each one can be undone)."""
        moved = 0
        progress = True
        while progress:
            progress = False
            ok, _ = self.move_waste_to_foundation()
            if ok:
                moved += 1
                progress = True
            for col in range(NUM_COLUMNS):
                ok, _ = self.move_tableau_to_foundation(col)
                if ok:
                    moved += 1
                    progress = True
        return moved

    # ------------------------------------------------------------------
    # Executing, undoing and redoing moves
    # ------------------------------------------------------------------
    def _execute(self, move, message):
        self._do(move)
        self.undo_stack.push(move)
        self.redo_stack.clear()          # a new move wipes the redo history
        self._check_finished()
        return True, message

    def _check_finished(self):
        if self.is_won() and self.end_time is None:
            self.end_time = time.time()

    def _apply_score(self, move, delta):
        new_score = max(0, self.score + delta)       # score never below 0
        move.score_delta = new_score - self.score    # remember the real change
        self.score = new_score

    def _reveal_top(self, col, move):
        """After cards leave a column, turn its new top card face up."""
        top = self.tableau[col].peek()
        move.flipped = top is not None and not top.face_up
        if move.flipped:
            top.flip()

    def _unreveal_top(self, col, move):
        if move.flipped:
            self.tableau[col].peek().flip()

    def _do(self, move):
        """Carry out a move (used for the first time AND for redo)."""
        kind = move.kind
        base = 0

        if kind == "DRAW":
            for _ in range(move.count):
                card = self.stock.dequeue()
                card.face_up = True
                self.waste.push(card)
            self._sync(("stock", 0), ("waste", 0))

        elif kind == "RECYCLE":
            cards = self.waste.to_list()             # bottom -> top
            self.waste.clear()
            for card in cards:
                card.face_up = False
                self.stock.enqueue(card)             # first drawn comes out first
            move.cards = cards
            base = SCORE_RECYCLE
            self._sync(("stock", 0), ("waste", 0))

        elif kind == "W2T":
            move_card(self.waste, self.tableau[move.dst])
            base = SCORE_WASTE_TO_TABLEAU
            self._sync(("waste", 0), ("tableau", move.dst))

        elif kind == "W2F":
            move_card(self.waste, self.foundation[move.dst])
            base = SCORE_TO_FOUNDATION
            self._sync(("waste", 0), ("foundation", move.dst))

        elif kind == "T2F":
            move_card(self.tableau[move.src], self.foundation[move.dst])
            self._reveal_top(move.src, move)
            base = SCORE_TO_FOUNDATION
            self._sync(("tableau", move.src), ("foundation", move.dst))

        elif kind == "T2T":
            move_run(self.tableau[move.src], self.tableau[move.dst], move.count)
            self._reveal_top(move.src, move)
            self._sync(("tableau", move.src), ("tableau", move.dst))

        elif kind == "F2T":
            move_card(self.foundation[move.src], self.tableau[move.dst])
            base = SCORE_FOUNDATION_TO_TABLEAU
            self._sync(("foundation", move.src), ("tableau", move.dst))

        if move.flipped:
            base += SCORE_FLIP
        self._apply_score(move, base)

    def _undo(self, move):
        """Exactly reverse a move."""
        kind = move.kind

        if kind == "DRAW":
            for _ in range(move.count):
                card = self.waste.pop()
                card.face_up = False
                self.stock.enqueue_front(card)       # back to the front of the queue
            self._sync(("stock", 0), ("waste", 0))

        elif kind == "RECYCLE":
            for _ in move.cards:
                card = self.stock.dequeue()
                card.face_up = True
                self.waste.push(card)
            self._sync(("stock", 0), ("waste", 0))

        elif kind == "W2T":
            move_card(self.tableau[move.dst], self.waste)
            self._sync(("waste", 0), ("tableau", move.dst))

        elif kind == "W2F":
            move_card(self.foundation[move.dst], self.waste)
            self._sync(("waste", 0), ("foundation", move.dst))

        elif kind == "T2F":
            self._unreveal_top(move.src, move)       # hide the revealed card again
            move_card(self.foundation[move.dst], self.tableau[move.src])
            self._sync(("tableau", move.src), ("foundation", move.dst))

        elif kind == "T2T":
            self._unreveal_top(move.src, move)
            move_run(self.tableau[move.dst], self.tableau[move.src], move.count)
            self._sync(("tableau", move.src), ("tableau", move.dst))

        elif kind == "F2T":
            move_card(self.tableau[move.dst], self.foundation[move.src])
            self._sync(("foundation", move.src), ("tableau", move.dst))

        self.score -= move.score_delta

    def undo(self):
        if self.undo_stack.is_empty():
            return False, "Nothing to undo."
        move = self.undo_stack.pop()
        self._undo(move)
        self.redo_stack.push(move)
        self.end_time = None
        return True, "Move undone."

    def redo(self):
        if self.redo_stack.is_empty():
            return False, "Nothing to redo."
        move = self.redo_stack.pop()
        self._do(move)
        self.undo_stack.push(move)
        self._check_finished()
        return True, "Move redone."

    # ------------------------------------------------------------------
    # Hints
    # ------------------------------------------------------------------
    def get_valid_moves(self):
        """All useful legal moves as (priority, kind, args, text),
        best first. Pointless moves (like shuffling a King between empty
        columns) are left out."""
        moves = []

        waste_top = self.waste.peek()
        if waste_top is not None:
            if self.foundation[waste_top.suit].can_accept(waste_top):
                moves.append((90, "W2F", (),
                              f"Move {waste_top} from the waste to the foundation."))
            for col in range(NUM_COLUMNS):
                if self.can_stack_on_tableau(waste_top, self.tableau[col]):
                    moves.append((60, "W2T", (col,),
                                  f"Move {waste_top} from the waste to column {col + 1}."))

        for col in range(NUM_COLUMNS):
            top = self.tableau[col].peek()
            if top is not None and self.foundation[top.suit].can_accept(top):
                moves.append((90, "T2F", (col,),
                              f"Move {top} from column {col + 1} to the foundation."))

        for src in range(NUM_COLUMNS):
            cards = self.tableau[src].to_list()
            for i, card in enumerate(cards):
                if not card.face_up:
                    continue
                run = cards[i:]
                if not self.is_valid_run(run):
                    continue
                parent = cards[i - 1] if i > 0 else None
                if parent is None:
                    if card.rank == 13:        # King already at the bottom
                        continue
                    priority = 50              # empties the column
                elif not parent.face_up:
                    priority = 70              # reveals a hidden card
                elif self.foundation[parent.suit].can_accept(parent):
                    priority = 65              # frees a card for the foundation
                else:
                    continue
                for dst in range(NUM_COLUMNS):
                    if dst != src and self.can_stack_on_tableau(card, self.tableau[dst]):
                        moves.append((priority, "T2T", (src, dst, len(run)),
                                      f"Move {len(run)} card(s) starting at {card} "
                                      f"from column {src + 1} to column {dst + 1}."))

        if not self.stock.is_empty():
            moves.append((10, "DRAW", (), "Draw from the stock."))
        elif not self.waste.is_empty():
            moves.append((5, "DRAW", (), "Turn the waste pile over to reuse it."))

        moves.sort(key=lambda m: m[0], reverse=True)
        return moves

    def hint(self):
        """A text suggestion for the best available move."""
        moves = self.get_valid_moves()
        return moves[0][3] if moves else "No moves available."

    def make_move(self, kind, *args):
        """Perform a move described by get_valid_moves()."""
        handlers = {
            "DRAW": self.draw,
            "W2T": self.move_waste_to_tableau,
            "W2F": self.move_waste_to_foundation,
            "T2F": self.move_tableau_to_foundation,
            "T2T": self.move_tableau_to_tableau,
            "F2T": self.move_foundation_to_tableau,
        }
        return handlers[kind](*args)

    # ------------------------------------------------------------------
    # Snapshot (used by tests to compare whole game states)
    # ------------------------------------------------------------------
    def snapshot(self):
        def enc(cards):
            return tuple((c.suit, c.rank, c.face_up) for c in cards)
        return (
            tuple(enc(p.to_list()) for p in self.tableau),
            tuple((s, enc(self.foundation[s].to_list())) for s in SUITS),
            enc(self.waste.to_list()),
            enc(self.stock.to_list()),
            self.score,
        )
