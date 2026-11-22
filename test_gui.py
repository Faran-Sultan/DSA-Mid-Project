"""
Tests for the graphical interface.

* TestGeometry / TestMouseLogic test gui_logic.py (pure Python).
* TestWindowSmoke runs the real SolitaireApp class from phase4_gui.py against
  a stand-in for tkinter, replaying clicks, drags and button presses, so the
  tests work on any machine (even without a display).

Run with:   python -m unittest -v
"""

import importlib
import sys
import unittest
from collections import namedtuple
from unittest import mock

import gui_logic as L
from phase1 import SUITS, Card
from phase3 import Game
from test_solitaire import blank_game, card

Ev = namedtuple("Ev", "x y")


def centre(rect):
    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)


# ---------------------------------------------------------------------------
class TestGeometry(unittest.TestCase):
    def test_everything_fits_on_the_canvas(self):
        g = Game(seed=3)
        for region in L.build_regions(g):
            x1, y1, x2, y2 = region.rect
            self.assertGreaterEqual(x1, 0)
            self.assertGreaterEqual(y1, 0)
            self.assertLessEqual(x2, L.CANVAS_W)
            self.assertLessEqual(y2, L.CANVAS_H)

    def test_tall_column_is_squeezed_to_fit(self):
        cards = [Card("Spades", 5, False) for _ in range(6)] + \
                [Card("Hearts", r, True) for r in range(13, 0, -1)]
        ys = L.card_ys(cards)
        self.assertEqual(len(ys), 19)
        self.assertEqual(ys, sorted(ys))
        self.assertLessEqual(ys[-1] + L.CARD_H, L.CANVAS_H)
        self.assertGreater(ys[1] - ys[0], 5)          # still readable

    def test_short_column_uses_normal_spacing(self):
        cards = [Card("Spades", 5, False), Card("Hearts", 4, True)]
        ys = L.card_ys(cards)
        self.assertEqual(ys[1] - ys[0], L.DOWN_OFFSET)

    def test_columns_do_not_overlap(self):
        for col in range(6):
            self.assertGreaterEqual(L.column_x(col + 1) - L.column_x(col), L.CARD_W)


# ---------------------------------------------------------------------------
class TestMouseLogic(unittest.TestCase):
    def test_hit_test_finds_each_kind(self):
        g = Game(seed=3)
        regions = L.build_regions(g)
        # stock
        r = L.hit_test(regions, *centre(L.stock_rect()))
        self.assertEqual(r.kind, "stock")
        # top card of column 5
        ys = L.card_ys(g.tableau[4].to_list())
        r = L.hit_test(regions, L.column_x(4) + 5, ys[-1] + 5)
        self.assertEqual((r.kind, r.col, r.idx), ("tableau", 4, 4))
        # a face-down card in the same column can be hit but not dragged
        r = L.hit_test(regions, L.column_x(4) + 5, ys[0] + 3)
        self.assertEqual((r.kind, r.idx), ("tableau", 0))
        self.assertIsNone(L.drag_cards(g, r))
        # empty space
        self.assertIsNone(L.hit_test(regions, 2, L.CANVAS_H - 2))

    def test_empty_column_region(self):
        g = blank_game()
        r = L.hit_test(L.build_regions(g), *centre(L.tableau_slot_rect(2)))
        self.assertEqual((r.kind, r.col), ("tableau_empty", 2))

    def test_drag_cards_picks_up_the_whole_run(self):
        g = blank_game()
        g.tableau[0].extend([card(9, "S", False), card(8, "H"), card(7, "C"), card(6, "D")])
        regions = L.build_regions(g)
        ys = L.card_ys(g.tableau[0].to_list())
        r = L.hit_test(regions, L.column_x(0) + 5, ys[1] + 5)
        picked = L.drag_cards(g, r)
        self.assertEqual([c.rank for c in picked], [8, 7, 6])
        self.assertEqual(L.drag_source(r), ("tableau", 0, 1))

    def test_waste_and_foundation_drag(self):
        g = blank_game()
        g.waste.push(card(4, "H"))
        g.foundation["Spades"].push(card(1, "S"))
        regions = L.build_regions(g)
        w = L.hit_test(regions, *centre(L.waste_top_rect(g)))
        self.assertEqual(w.kind, "waste")
        self.assertEqual(L.drag_cards(g, w)[0].rank, 4)
        f = L.hit_test(regions, *centre(L.foundation_rect("Spades")))
        self.assertEqual(f.kind, "foundation")
        slot = L.hit_test(regions, *centre(L.foundation_rect("Hearts")))
        self.assertEqual(slot.kind, "foundation_slot")
        self.assertIsNone(L.drag_cards(g, slot))

    def test_drop_target(self):
        # centre of a card dropped on column 3, below the top row
        cx = L.column_x(3) + L.CARD_W / 2
        self.assertEqual(L.drop_target(cx, L.TABLEAU_Y + 80), ("tableau", 3))
        # slightly off-centre still counts
        self.assertEqual(L.drop_target(cx + 20, L.TABLEAU_Y + 200), ("tableau", 3))
        # top row over the foundations
        self.assertEqual(L.drop_target(L.column_x(4), L.TOP_Y + 50), ("foundation",))
        # top row over the stock/waste area -> nothing
        self.assertIsNone(L.drop_target(L.column_x(0), L.TOP_Y + 50))
        # off the right edge
        self.assertIsNone(L.drop_target(L.CANVAS_W + 200, L.TABLEAU_Y + 50))

    def test_attempt_drop_waste_and_foundation(self):
        g = blank_game()
        g.waste.push(card(1, "H"))
        ok, _ = L.attempt_drop(g, ("waste",), [g.waste.peek()], ("foundation",))
        self.assertTrue(ok)
        self.assertEqual(len(g.foundation["Hearts"]), 1)

    def test_attempt_drop_tableau_run(self):
        g = blank_game()
        g.tableau[0].append(card(8, "H"))
        g.tableau[1].extend([card(7, "S"), card(6, "H")])
        run = g.tableau[1].top_cards(2)
        ok, _ = L.attempt_drop(g, ("tableau", 1, 0), run, ("tableau", 0))
        self.assertTrue(ok)
        self.assertEqual(len(g.tableau[0]), 3)

    def test_attempt_drop_rejections(self):
        g = blank_game()
        g.tableau[0].extend([card(9, "S"), card(8, "H")])
        g.tableau[1].append(card(5, "C"))
        g.foundation["Hearts"].push(card(1, "H"))
        run = g.tableau[0].top_cards(2)
        # several cards to the foundation
        ok, msg = L.attempt_drop(g, ("tableau", 0, 0), run, ("foundation",))
        self.assertFalse(ok)
        # illegal tableau move
        ok, _ = L.attempt_drop(g, ("tableau", 1, 0), g.tableau[1].top_cards(1), ("tableau", 0))
        self.assertFalse(ok)
        # no target
        ok, _ = L.attempt_drop(g, ("tableau", 1, 0), g.tableau[1].top_cards(1), None)
        self.assertFalse(ok)
        # dropping back on the same column / the same foundation does nothing
        ok, _ = L.attempt_drop(g, ("tableau", 0, 1), g.tableau[0].top_cards(1), ("tableau", 0))
        self.assertIsNone(ok)
        ok, _ = L.attempt_drop(g, ("foundation", "Hearts"), [g.foundation["Hearts"].peek()],
                               ("foundation",))
        self.assertIsNone(ok)
        self.assertEqual(len(g.tableau[0]), 2)       # nothing moved

    def test_foundation_back_to_tableau(self):
        g = blank_game()
        for r in (1, 2, 3):
            g.foundation["Hearts"].push(card(r, "H"))
        g.tableau[0].append(card(4, "S"))
        ok, _ = L.attempt_drop(g, ("foundation", "Hearts"),
                               [g.foundation["Hearts"].peek()], ("tableau", 0))
        self.assertTrue(ok)

    def test_hint_rects_for_every_kind(self):
        seen = set()
        for seed in range(30):
            for draw in (1, 3):
                g = Game(draw_count=draw, seed=seed)
                for _ in range(60):
                    moves = g.get_valid_moves()
                    if not moves:
                        break
                    for _, kind, args, _ in moves:
                        rects = L.hint_rects(g, kind, args)
                        self.assertTrue(rects, kind)
                        for x1, y1, x2, y2 in rects:
                            self.assertTrue(0 <= x1 < x2 <= L.CANVAS_W)
                            self.assertTrue(0 <= y1 < y2 <= L.CANVAS_H)
                        seen.add(kind)
                    _, kind, args, _ = moves[0]
                    g.make_move(kind, *args)
        self.assertEqual(seen, {"DRAW", "W2F", "W2T", "T2F", "T2T"})


# ---------------------------------------------------------------------------
class FakeVar:
    """Stand-in for tkinter.IntVar."""
    def __init__(self, master=None, value=0):
        self._v = value

    def get(self):
        return self._v

    def set(self, value):
        self._v = value


class TestWindowSmoke(unittest.TestCase):
    """Drive the real SolitaireApp with a fake tkinter."""

    @classmethod
    def setUpClass(cls):
        cls.fake_tk = mock.MagicMock(name="tkinter")
        cls.fake_tk.IntVar = FakeVar
        cls.patcher = mock.patch.dict(sys.modules, {"tkinter": cls.fake_tk})
        cls.patcher.start()
        sys.modules.pop("phase4_gui", None)
        cls.gui = importlib.import_module("phase4_gui")

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        sys.modules.pop("phase4_gui", None)

    def setUp(self):
        self.fake_tk.messagebox.askyesno.reset_mock()
        self.fake_tk.messagebox.askyesno.return_value = True
        self.app = self.gui.SolitaireApp(mock.MagicMock(), draw_count=1, seed=5)

    def click(self, x, y):
        self.app.on_press(Ev(x, y))
        self.app.on_release(Ev(x, y))

    def drag(self, start, end):
        self.app.on_press(Ev(*start))
        self.app.on_motion(Ev((start[0] + end[0]) // 2, (start[1] + end[1]) // 2))
        self.app.on_motion(Ev(*end))
        self.app.on_release(Ev(*end))

    def test_window_draws(self):
        self.assertTrue(self.app.canvas.create_polygon.called)
        self.assertTrue(self.app.canvas.create_text.called)
        self.assertEqual(len(self.app.regions), len(L.build_regions(self.app.game)))

    def test_click_stock_draws_a_card(self):
        self.click(*centre(L.stock_rect()))
        self.assertEqual(len(self.app.game.waste), 1)
        self.assertEqual(self.app.game.move_count, 1)

    def test_click_stock_until_recycle(self):
        for _ in range(25):
            self.click(*centre(L.stock_rect()))
        self.assertEqual(len(self.app.game.stock), 24)    # 24 draws + recycle
        self.assertTrue(self.app.game.waste.is_empty())

    def test_drag_run_between_columns(self):
        """Find a real legal tableau move and perform it with the mouse."""
        for seed in range(60):
            app = self.gui.SolitaireApp(mock.MagicMock(), draw_count=1, seed=seed)
            move = next((m for m in app.game.get_valid_moves() if m[1] == "T2T"), None)
            if move is None:
                continue
            _, _, (src, dst, count), _ = move
            g = app.game
            ys = L.card_ys(g.tableau[src].to_list())
            idx = len(g.tableau[src]) - count
            start = (L.column_x(src) + 10, ys[idx] + 10)
            target = L.tableau_top_rect(g, dst)
            end = (target[0] + 10, target[1] + 10)
            before = (len(g.tableau[src]), len(g.tableau[dst]))
            app.on_press(Ev(*start))
            self.assertIsNotNone(app.drag)
            app.on_motion(Ev(*end))
            app.on_release(Ev(*end))
            self.assertIsNone(app.drag)
            self.assertEqual((len(g.tableau[src]), len(g.tableau[dst])),
                             (before[0] - count, before[1] + count))
            self.assertTrue(g.check_consistency())
            return
        self.fail("no seed produced a tableau move")

    def test_illegal_drop_changes_nothing(self):
        g = self.app.game
        before = g.snapshot()
        ys = L.card_ys(g.tableau[6].to_list())
        start = (L.column_x(6) + 10, ys[-1] + 10)
        # drop in the stock area (never a legal target)
        self.drag(start, (L.column_x(0) + 10, L.TOP_Y + 20))
        self.assertEqual(g.snapshot(), before)

    def test_click_without_moving_does_nothing(self):
        g = self.app.game
        before = g.snapshot()
        ys = L.card_ys(g.tableau[6].to_list())
        self.click(L.column_x(6) + 10, ys[-1] + 10)
        self.assertEqual(g.snapshot(), before)

    def test_double_click_sends_ace_to_foundation(self):
        app = self.app
        app.game = blank_game()
        app.game.tableau[2].extend([card(9, "C", False), card(1, "D")])
        app.game.positions = app.game._build_positions()
        app.redraw()
        ys = L.card_ys(app.game.tableau[2].to_list())
        app.on_double(Ev(L.column_x(2) + 10, ys[-1] + 10))
        self.assertEqual(len(app.game.foundation["Diamonds"]), 1)
        self.assertTrue(app.game.tableau[2].peek().face_up)     # 9C flipped

    def test_drag_ace_to_foundation(self):
        app = self.app
        app.game = blank_game()
        app.game.tableau[1].append(card(1, "S"))
        app.game.positions = app.game._build_positions()
        app.redraw()
        ys = L.card_ys(app.game.tableau[1].to_list())
        start = (L.column_x(1) + 10, ys[-1] + 10)
        end = (L.column_x(3) + 10, L.TOP_Y + 10)
        self.drag(start, end)
        self.assertEqual(len(app.game.foundation["Spades"]), 1)

    def test_buttons(self):
        app = self.app
        app.on_hint()
        self.assertIsNotNone(app.hint)
        app.on_press(Ev(*centre(L.stock_rect())))             # clears the hint
        self.assertIsNone(app.hint)
        app.on_undo()
        self.assertEqual(app.game.move_count, 0)
        app.on_redo()
        self.assertEqual(app.game.move_count, 1)
        app.on_auto()                                          # nothing to move
        app.on_undo()
        app.on_new()                                           # no moves: no prompt
        self.assertEqual(app.game.move_count, 0)

    def test_new_game_asks_before_abandoning(self):
        app = self.app
        app.on_press(Ev(*centre(L.stock_rect())))
        old = app.game
        self.fake_tk.messagebox.askyesno.return_value = False
        app.on_new()
        self.assertIs(app.game, old)                           # cancelled
        self.fake_tk.messagebox.askyesno.return_value = True
        app.on_new()
        self.assertIsNot(app.game, old)

    def test_switching_draw_mode(self):
        app = self.app
        app.mode_var.set(3)
        app.on_mode_change()
        self.assertEqual(app.game.draw_count, 3)
        self.click(*centre(L.stock_rect()))
        self.assertEqual(len(app.game.waste), 3)
        self.fake_tk.messagebox.askyesno.return_value = False
        app.mode_var.set(1)
        app.on_mode_change()
        self.assertEqual(app.game.draw_count, 3)               # refused
        self.assertEqual(app.mode_var.get(), 3)                # radio button reverted

    def test_winning_shows_banner_and_offers_replay(self):
        app = self.app
        g = app.game = blank_game()
        for suit, letter in (("Hearts", "H"), ("Diamonds", "D"),
                             ("Clubs", "C"), ("Spades", "S")):
            for r in range(1, 13):
                g.foundation[suit].push(card(r, letter))
        g.tableau[0].append(card(13, "H"))
        g.waste.push(card(13, "S"))
        g.tableau[1].append(card(13, "D"))
        g.tableau[2].append(card(13, "C"))
        g.positions = g._build_positions()
        app.redraw()
        app.on_auto()                                          # moves all four kings
        self.assertTrue(g.is_won())
        self.assertTrue(app.win_shown)
        app.ask_play_again()                                   # user says yes
        self.assertFalse(app.win_shown)
        self.assertFalse(app.game.is_won())
        before = app.game.snapshot()
        app.on_press(Ev(*centre(L.stock_rect())))              # game is playable again
        self.assertNotEqual(app.game.snapshot(), before)

    def test_bot_plays_through_the_window(self):
        """Play 150 hinted moves using only mouse events."""
        app = self.app
        for _ in range(150):
            g = app.game
            moves = g.get_valid_moves()
            if not moves or g.is_won():
                break
            _, kind, args, _ = moves[0]
            before = g.snapshot()
            if kind == "DRAW":
                self.click(*centre(L.stock_rect()))
            elif kind in ("W2F", "W2T"):
                start = centre(L.waste_top_rect(g))
                dest = (L.foundation_rect(g.waste.peek().suit) if kind == "W2F"
                        else L.tableau_top_rect(g, args[0]))
                self.drag(start, (dest[0] + 40, dest[1] + 56))
            elif kind == "T2F":
                rect = L.tableau_top_rect(g, args[0])
                dest = L.foundation_rect(g.tableau[args[0]].peek().suit)
                self.drag(centre(rect), (dest[0] + 40, dest[1] + 56))
            else:
                src, dst, count = args
                ys = L.card_ys(g.tableau[src].to_list())
                idx = len(g.tableau[src]) - count
                start = (L.column_x(src) + 40, ys[idx] + 10)
                dest = L.tableau_top_rect(g, dst)
                self.drag(start, (dest[0] + 40, dest[1] + 10))
            self.assertNotEqual(app.game.snapshot(), before, f"{kind} {args} did nothing")
            self.assertTrue(app.game.check_consistency())


if __name__ == "__main__":
    unittest.main(verbosity=2)
