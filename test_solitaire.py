"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Validation and Testing

Run with:   python -m unittest -v
Covers: legal moves, card flipping, win condition, game flow, undo/redo,
stockpile behaviour and the hand-written data structures.
"""

import random
import unittest

from phase1 import Card, Deck, SUITS
from phase2 import Stack, Queue, TableauPile, FoundationPile
from phase3 import Game

LETTER = {"H": "Hearts", "D": "Diamonds", "C": "Clubs", "S": "Spades"}


def card(rank, suit, up=True):
    """card(7, 'H') -> 7 of Hearts, face up."""
    return Card(LETTER[suit], rank, up)


def blank_game(draw_count=1):
    """A game with every pile emptied, so tests can set up exact positions."""
    g = Game(draw_count=draw_count, seed=1)
    g.tableau = [TableauPile() for _ in range(7)]
    g.foundation = {s: FoundationPile(s) for s in SUITS}
    g.waste = Stack()
    g.stock = Queue()
    g.undo_stack, g.redo_stack = Stack(), Stack()
    g.score = 0
    g.positions = {}
    return g


# ---------------------------------------------------------------------------
class TestPhase1CardAndDeck(unittest.TestCase):
    def test_card_color_and_flip(self):
        c = Card("Hearts", 12)
        self.assertEqual(c.color, "Red")
        self.assertFalse(c.face_up)
        c.flip()
        self.assertTrue(c.face_up)
        self.assertEqual(Card("Spades", 1).color, "Black")

    def test_invalid_card(self):
        with self.assertRaises(ValueError):
            Card("Stars", 5)
        with self.assertRaises(ValueError):
            Card("Spades", 14)

    def test_deck_has_52_unique_cards(self):
        d = Deck()
        self.assertEqual(len(d), 52)
        self.assertEqual(len({(c.suit, c.rank) for c in d.cards}), 52)

    def test_shuffle_keeps_cards(self):
        d = Deck()
        before = sorted((c.suit, c.rank) for c in d.cards)
        d.shuffle()
        self.assertEqual(before, sorted((c.suit, c.rank) for c in d.cards))


class TestDataStructures(unittest.TestCase):
    def test_stack_is_lifo(self):
        s = Stack()
        for i in (1, 2, 3):
            s.push(i)
        self.assertEqual([s.pop(), s.pop(), s.pop()], [3, 2, 1])
        with self.assertRaises(IndexError):
            s.pop()

    def test_queue_is_fifo(self):
        q = Queue()
        for i in (1, 2, 3):
            q.enqueue(i)
        q.enqueue_front(0)
        self.assertEqual([q.dequeue() for _ in range(4)], [0, 1, 2, 3])
        with self.assertRaises(IndexError):
            q.dequeue()

    def test_linked_list_pile(self):
        p = TableauPile()
        p.extend([card(r, "S") for r in (9, 8, 7, 6)])
        self.assertEqual(len(p), 4)
        self.assertEqual(p.peek().rank, 6)
        self.assertEqual([c.rank for c in p.top_cards(2)], [7, 6])
        run = p.pop_n(3)
        self.assertEqual([c.rank for c in run], [8, 7, 6])
        self.assertEqual([c.rank for c in p.to_list()], [9])
        self.assertEqual(p.pop().rank, 9)
        self.assertTrue(p.is_empty())
        self.assertIsNone(p.peek())
        with self.assertRaises(IndexError):
            p.pop()
        with self.assertRaises(ValueError):
            p.pop_n(1)

    def test_foundation_pile_rules(self):
        f = FoundationPile("Hearts")
        self.assertFalse(f.can_accept(card(2, "H")))      # must start with Ace
        self.assertFalse(f.can_accept(card(1, "S")))      # wrong suit
        f.push(card(1, "H"))
        self.assertTrue(f.can_accept(card(2, "H")))
        self.assertFalse(f.can_accept(card(3, "H")))      # skipped a rank


class TestSetup(unittest.TestCase):
    def test_initial_deal(self):
        g = Game(seed=7)
        for col in range(7):
            cards = g.tableau[col].to_list()
            self.assertEqual(len(cards), col + 1)
            self.assertTrue(all(not c.face_up for c in cards[:-1]))
            self.assertTrue(cards[-1].face_up)
        self.assertEqual(len(g.stock), 24)
        self.assertTrue(all(not c.face_up for c in g.stock))
        self.assertTrue(g.waste.is_empty())
        self.assertTrue(all(len(p) == 0 for p in g.foundation.values()))
        self.assertTrue(g.check_consistency())          # 52 cards, all located
        self.assertFalse(g.is_won())

    def test_same_seed_same_deal(self):
        self.assertEqual(Game(seed=5).snapshot(), Game(seed=5).snapshot())

    def test_position_dictionary(self):
        g = Game(seed=3)
        top = g.tableau[4].peek()
        self.assertEqual(g.locate(top), ("tableau", 4, 4))
        first = g.stock.peek()
        self.assertEqual(g.locate(first), ("stock", 0, 0))


# ---------------------------------------------------------------------------
class TestLegalMoves(unittest.TestCase):
    def test_alternating_colour_and_rank(self):
        g = blank_game()
        g.tableau[0].append(card(7, "S"))            # black 7
        g.tableau[1].append(card(6, "H"))            # red 6 -> legal on it
        self.assertTrue(g.move_tableau_to_tableau(1, 0)[0])
        self.assertEqual(g.tableau[0].peek().rank, 6)

    def test_wrong_rank_and_same_colour_rejected(self):
        g = blank_game()
        g.tableau[0].append(card(7, "S"))
        g.tableau[1].append(card(6, "C"))     # same colour as 7S
        g.tableau[2].append(card(5, "H"))     # right colour, rank gap
        self.assertFalse(g.move_tableau_to_tableau(1, 0)[0])
        self.assertFalse(g.move_tableau_to_tableau(2, 0)[0])

    def test_only_king_on_empty_column(self):
        g = blank_game()
        g.tableau[0].append(card(13, "H"))
        g.tableau[1].append(card(12, "S"))
        self.assertFalse(g.move_tableau_to_tableau(1, 2)[0])    # Queen -> empty
        self.assertTrue(g.move_tableau_to_tableau(0, 2)[0])     # King  -> empty

    def test_foundation_rules(self):
        g = blank_game()
        g.tableau[0].append(card(2, "H"))
        g.tableau[1].append(card(1, "H"))
        self.assertFalse(g.move_tableau_to_foundation(0)[0])    # 2 before Ace
        self.assertTrue(g.move_tableau_to_foundation(1)[0])     # Ace
        self.assertTrue(g.move_tableau_to_foundation(0)[0])     # then the 2

    def test_move_run_of_cards(self):
        g = blank_game()
        g.tableau[0].append(card(8, "H"))
        g.tableau[1].extend([card(7, "S"), card(6, "H"), card(5, "C")])
        ok, _ = g.move_tableau_to_tableau(1, 0, 3)
        self.assertTrue(ok)
        self.assertEqual([c.rank for c in g.tableau[0]], [8, 7, 6, 5])
        self.assertTrue(g.tableau[1].is_empty())

    def test_cannot_move_face_down_or_too_many(self):
        g = blank_game()
        g.tableau[0].append(card(8, "H"))
        g.tableau[1].extend([card(9, "S", False), card(7, "S")])
        self.assertFalse(g.move_tableau_to_tableau(1, 0, 2)[0])  # includes face-down
        self.assertFalse(g.move_tableau_to_tableau(1, 0, 5)[0])  # more than exist
        self.assertFalse(g.move_tableau_to_tableau(1, 1, 1)[0])  # same column
        self.assertFalse(g.move_tableau_to_tableau(1, 9, 1)[0])  # bad column

    def test_broken_run_rejected(self):
        g = blank_game()
        g.tableau[0].append(card(9, "H"))
        g.tableau[1].extend([card(8, "S"), card(6, "H")])     # gap in the run
        self.assertFalse(g.move_tableau_to_tableau(1, 0, 2)[0])

    def test_waste_moves(self):
        g = blank_game()
        g.tableau[0].append(card(7, "S"))
        g.waste.push(card(6, "H"))
        self.assertFalse(g.move_waste_to_foundation()[0])
        self.assertTrue(g.move_waste_to_tableau(0)[0])
        self.assertTrue(g.waste.is_empty())
        self.assertFalse(g.move_waste_to_tableau(0)[0])        # empty waste

    def test_foundation_back_to_tableau(self):
        g = blank_game()
        for r in (1, 2, 3):
            g.foundation["Hearts"].push(card(r, "H"))
        g.tableau[0].append(card(4, "S"))
        ok, _ = g.move_foundation_to_tableau("Hearts", 0)
        self.assertTrue(ok)
        self.assertEqual(g.tableau[0].peek().rank, 3)
        self.assertFalse(g.move_foundation_to_tableau("Clubs", 0)[0])  # empty


# ---------------------------------------------------------------------------
class TestCardFlipping(unittest.TestCase):
    def test_flip_after_tableau_to_tableau(self):
        g = blank_game()
        g.tableau[0].extend([card(9, "C", False), card(5, "H")])
        g.tableau[1].append(card(6, "S"))
        ok, _ = g.move_tableau_to_tableau(0, 1)
        self.assertTrue(ok)
        self.assertTrue(g.tableau[0].peek().face_up)      # 9C turned over
        self.assertEqual(g.score, 5)                      # +5 for the flip

    def test_flip_after_move_to_foundation(self):
        g = blank_game()
        g.tableau[0].extend([card(3, "D", False), card(1, "S")])
        self.assertTrue(g.move_tableau_to_foundation(0)[0])
        self.assertTrue(g.tableau[0].peek().face_up)
        self.assertEqual(g.score, 15)                     # 10 + 5

    def test_no_flip_when_card_below_already_face_up(self):
        g = blank_game()
        g.tableau[0].extend([card(7, "S"), card(6, "H")])
        g.tableau[1].append(card(7, "C"))
        self.assertTrue(g.move_tableau_to_tableau(0, 1)[0])
        self.assertEqual(g.score, 0)

    def test_undo_hides_card_again(self):
        g = blank_game()
        g.tableau[0].extend([card(9, "C", False), card(5, "H")])
        g.tableau[1].append(card(6, "S"))
        g.move_tableau_to_tableau(0, 1)
        g.undo()
        self.assertFalse(g.tableau[0].to_list()[0].face_up)
        self.assertEqual(len(g.tableau[0]), 2)
        self.assertEqual(g.score, 0)


# ---------------------------------------------------------------------------
class TestStockpile(unittest.TestCase):
    def test_draw_one_is_fifo(self):
        g = Game(draw_count=1, seed=11)
        order = [(c.suit, c.rank) for c in g.stock]
        for expected in order[:3]:
            g.draw()
            top = g.waste.peek()
            self.assertEqual((top.suit, top.rank), expected)
            self.assertTrue(top.face_up)
        self.assertEqual(len(g.stock), 21)

    def test_draw_three(self):
        g = Game(draw_count=3, seed=11)
        g.draw()
        self.assertEqual(len(g.waste), 3)
        self.assertEqual(len(g.stock), 21)

    def test_recycle_keeps_order(self):
        g = Game(draw_count=1, seed=11)
        order = [(c.suit, c.rank) for c in g.stock]
        for _ in range(24):
            g.draw()
        self.assertTrue(g.stock.is_empty())
        ok, _ = g.draw()                                  # recycle
        self.assertTrue(ok)
        self.assertEqual(len(g.stock), 24)
        self.assertTrue(g.waste.is_empty())
        self.assertEqual([(c.suit, c.rank) for c in g.stock], order)
        self.assertTrue(all(not c.face_up for c in g.stock))

    def test_draw_with_nothing_left(self):
        g = blank_game()
        self.assertFalse(g.draw()[0])

    def test_undo_draw_and_recycle(self):
        g = Game(draw_count=3, seed=2)
        start = g.snapshot()
        for _ in range(8):
            g.draw()                                      # 24 cards -> stock empty
        g.draw()                                          # recycle
        for _ in range(9):
            self.assertTrue(g.undo()[0])
            self.assertTrue(g.check_consistency())
        self.assertEqual(g.snapshot(), start)


# ---------------------------------------------------------------------------
class TestWinCondition(unittest.TestCase):
    def test_win_detected(self):
        g = blank_game()
        for suit in ("H", "D", "C"):
            for r in range(1, 14):
                g.foundation[LETTER[suit]].push(card(r, suit))
        for r in range(1, 13):
            g.foundation["Spades"].push(card(r, "S"))
        g.tableau[3].append(card(13, "S"))               # last card, in the tableau
        self.assertFalse(g.is_won())
        self.assertTrue(g.move_tableau_to_foundation(3)[0])
        self.assertTrue(g.is_won())
        self.assertIsNotNone(g.end_time)                 # timer stopped

    def test_last_card_in_waste(self):
        g = blank_game()
        for suit in ("H", "D", "C", "S"):
            top = 12 if suit == "H" else 13
            for r in range(1, top + 1):
                g.foundation[LETTER[suit]].push(card(r, suit))
        g.waste.push(card(13, "H"))
        self.assertFalse(g.is_won())
        self.assertTrue(g.move_waste_to_foundation()[0])
        self.assertTrue(g.is_won())

    def test_not_won_with_cards_left(self):
        g = Game(seed=4)
        self.assertFalse(g.is_won())

    def test_undo_win_restarts_clock(self):
        g = blank_game()
        for suit in ("H", "D", "C", "S"):
            for r in range(1, 14 if suit != "S" else 13):
                g.foundation[LETTER[suit]].push(card(r, suit))
        g.waste.push(card(13, "S"))
        g.move_waste_to_foundation()
        self.assertTrue(g.is_won())
        g.undo()
        self.assertFalse(g.is_won())
        self.assertIsNone(g.end_time)


# ---------------------------------------------------------------------------
class TestUndoRedoAndScore(unittest.TestCase):
    def test_undo_redo_single_move(self):
        g = blank_game()
        g.waste.push(card(1, "S"))
        g.positions = g._build_positions()
        before = g.snapshot()
        g.move_waste_to_foundation()
        after = g.snapshot()
        self.assertEqual(g.score, 10)
        g.undo()
        self.assertEqual(g.snapshot(), before)
        g.redo()
        self.assertEqual(g.snapshot(), after)

    def test_new_move_clears_redo(self):
        g = Game(seed=9)
        g.draw()
        g.undo()
        self.assertEqual(len(g.redo_stack), 1)
        g.draw()
        self.assertEqual(len(g.redo_stack), 0)
        self.assertFalse(g.redo()[0])

    def test_nothing_to_undo(self):
        self.assertFalse(Game(seed=1).undo()[0])

    def test_score_never_negative(self):
        g = blank_game()
        g.foundation["Hearts"].push(card(1, "H"))
        g.tableau[1].append(card(2, "S"))
        ok, _ = g.move_foundation_to_tableau("Hearts", 1)   # normally -15
        self.assertTrue(ok)
        self.assertEqual(g.score, 0)                        # clamped at 0
        g.undo()
        self.assertEqual(g.score, 0)

    def test_auto_move(self):
        g = blank_game()
        g.tableau[0].extend([card(2, "H"), card(1, "H")])   # Ace sits on the 2
        self.assertEqual(g.auto_move_to_foundation(), 2)
        self.assertEqual(len(g.foundation["Hearts"]), 2)
        self.assertEqual(g.auto_move_to_foundation(), 0)


# ---------------------------------------------------------------------------
class TestFullGameFlow(unittest.TestCase):
    """Play whole games with a bot and check nothing ever breaks."""

    def _play(self, game, rng, steps):
        for _ in range(steps):
            moves = game.get_valid_moves()
            if not moves:
                break
            if rng is None:
                _, kind, args, _ = moves[0]                   # best move
            else:
                _, kind, args, _ = rng.choice(moves)          # random legal move
            ok, msg = game.make_move(kind, *args)
            self.assertTrue(ok, msg)                          # suggested => legal
            self.assertTrue(game.check_consistency())
            if game.is_won():
                break

    def test_hint_bot_full_flow_and_undo_all(self):
        for draw_count in (1, 3):
            for seed in range(5):
                g = Game(draw_count=draw_count, seed=seed)
                start = g.snapshot()
                self._play(g, None, 300)
                end = g.snapshot()
                moves_made = len(g.undo_stack)
                for _ in range(moves_made):
                    self.assertTrue(g.undo()[0])
                self.assertEqual(g.snapshot(), start)         # back to the deal
                self.assertTrue(g.check_consistency())
                for _ in range(moves_made):
                    self.assertTrue(g.redo()[0])
                self.assertEqual(g.snapshot(), end)

    def test_random_bot_full_flow_and_undo_all(self):
        for seed in range(5):
            g = Game(draw_count=3 if seed % 2 else 1, seed=100 + seed)
            start = g.snapshot()
            self._play(g, random.Random(seed), 400)
            while g.undo()[0]:
                pass
            self.assertEqual(g.snapshot(), start)
            self.assertTrue(g.check_consistency())

    def test_always_52_cards(self):
        g = Game(seed=21)
        self._play(g, random.Random(3), 200)
        total = (len(g.stock) + len(g.waste)
                 + sum(len(p) for p in g.tableau)
                 + sum(len(p) for p in g.foundation.values()))
        self.assertEqual(total, 52)


if __name__ == "__main__":
    unittest.main(verbosity=2)
