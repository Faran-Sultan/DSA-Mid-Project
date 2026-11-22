"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Phase 4: Graphical User Interface (tkinter)

Run with:
    python phase4_gui.py              (draw 1 card at a time)
    python phase4_gui.py --draw 3     (draw 3 cards at a time)
    python phase4_gui.py --seed 42    (same deal every time)

How to play:
    * Click the stock (top-left) to draw. Click the empty stock to reuse the waste.
    * Drag cards (and runs of cards) between columns, or up to the foundations.
    * Double-click a card to send it to the foundation.
    * Buttons: New Game, Undo, Redo, Hint, Auto.   Keys: Ctrl+Z / Ctrl+Y / Ctrl+N / H
"""

import argparse
import tkinter as tk
from tkinter import messagebox

from phase1 import SUITS, SUIT_SYMBOLS
from phase3 import Game
import gui_logic as L

# Colours and fonts
FELT = "#1e6b3a"
SLOT_OUTLINE = "#4f9a68"
CARD_FACE = "#fcfcf8"
CARD_EDGE = "#4a4a4a"
CARD_BACK = "#2b5aa3"
CARD_BACK_EDGE = "#173a70"
RED = "#c0392b"
BLACK = "#1b1b1b"
HINT_COLOR = "#ffd028"
FONT = "Arial"


class SolitaireApp:
    def __init__(self, root, draw_count=1, seed=None):
        self.root = root
        self.game = Game(draw_count=draw_count, seed=seed)
        self.drag = None             # info about the drag in progress
        self.hint = None             # (kind, args) of the hint being shown
        self.regions = []
        self.win_shown = False

        root.title("Klondike Solitaire - CSC200")
        root.resizable(False, False)
        self._build_widgets(draw_count)
        self._bind_events()
        self.set_status("Welcome! Click the stock to draw. Drag cards to move them.")
        self.redraw()
        self.tick()

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------
    def _build_widgets(self, draw_count):
        bar = tk.Frame(self.root, bg="#14472a", padx=8, pady=6)
        bar.pack(fill="x")

        for text, command in (("New Game", self.on_new), ("Undo", self.on_undo),
                              ("Redo", self.on_redo), ("Hint", self.on_hint),
                              ("Auto", self.on_auto)):
            tk.Button(bar, text=text, width=8, command=command).pack(side="left", padx=3)

        self.mode_var = tk.IntVar(value=draw_count)
        for value in (1, 3):
            tk.Radiobutton(bar, text=f"Draw {value}", variable=self.mode_var,
                           value=value, command=self.on_mode_change,
                           bg="#14472a", fg="white", selectcolor="#0d2f1b",
                           activebackground="#14472a", activeforeground="white"
                           ).pack(side="left", padx=(10 if value == 1 else 0, 0))

        self.stats_label = tk.Label(bar, text="", bg="#14472a", fg="white",
                                    font=(FONT, 11, "bold"))
        self.stats_label.pack(side="right", padx=6)

        self.canvas = tk.Canvas(self.root, width=L.CANVAS_W, height=L.CANVAS_H,
                                bg=FELT, highlightthickness=0)
        self.canvas.pack()

        self.status_label = tk.Label(self.root, text="", anchor="w", bg="#0d2f1b",
                                     fg="white", font=(FONT, 10), padx=8, pady=4)
        self.status_label.pack(fill="x")

    def _bind_events(self):
        c = self.canvas
        c.bind("<Button-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_motion)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double)
        self.root.bind("<Control-z>", lambda e: self.on_undo())
        self.root.bind("<Control-y>", lambda e: self.on_redo())
        self.root.bind("<Control-n>", lambda e: self.on_new())
        self.root.bind("h", lambda e: self.on_hint())

    # ------------------------------------------------------------------
    # Status, stats and timer
    # ------------------------------------------------------------------
    def set_status(self, message, error=False):
        self.status_label.config(text=message,
                                 fg="#ffb3b3" if error else "white")

    def update_stats(self):
        g = self.game
        self.stats_label.config(
            text=f"Score: {g.score}     Moves: {g.move_count}     Time: {g.elapsed_str()}")

    def tick(self):
        self.update_stats()
        self.root.after(500, self.tick)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def rounded_rect(self, x1, y1, x2, y2, r=8, **options):
        points = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1,
                  x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2,
                  x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(points, smooth=True, **options)

    def draw_slot(self, rect, label=""):
        x1, y1, x2, y2 = rect
        self.rounded_rect(x1, y1, x2, y2, fill="", outline=SLOT_OUTLINE, width=2)
        if label:
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label,
                                    font=(FONT, 28), fill=SLOT_OUTLINE)

    def draw_card(self, x, y, card, tag="card"):
        c = self.canvas
        if card.face_up:
            self.rounded_rect(x, y, x + L.CARD_W, y + L.CARD_H, fill=CARD_FACE,
                              outline=CARD_EDGE, width=1, tags=(tag,))
            colour = RED if card.color == "Red" else BLACK
            symbol = SUIT_SYMBOLS[card.suit]
            c.create_text(x + 7, y + 5, text=f"{card.label}{symbol}", anchor="nw",
                          font=(FONT, 14, "bold"), fill=colour, tags=(tag,))
            c.create_text(x + L.CARD_W / 2, y + L.CARD_H / 2 + 8, text=symbol,
                          font=(FONT, 36), fill=colour, tags=(tag,))
        else:
            self.rounded_rect(x, y, x + L.CARD_W, y + L.CARD_H, fill=CARD_BACK,
                              outline=CARD_BACK_EDGE, width=1, tags=(tag,))
            self.rounded_rect(x + 6, y + 6, x + L.CARD_W - 6, y + L.CARD_H - 6, r=6,
                              fill="", outline="#8fb4ea", width=2, tags=(tag,))

    def redraw(self):
        c = self.canvas
        g = self.game
        c.delete("all")
        drag = self.drag
        source = drag["source"] if drag else None

        # --- stock -------------------------------------------------------
        x, y = L.stock_rect()[:2]
        if len(g.stock):
            self.draw_card(x, y, g.stock.peek())
            c.create_text(x + L.CARD_W / 2, y + L.CARD_H + 10,
                          text=f"{len(g.stock)} left", font=(FONT, 9), fill="white")
        else:
            self.draw_slot(L.stock_rect())
            if not g.waste.is_empty():       # hint that clicking recycles the waste
                cx, cy = x + L.CARD_W / 2, y + L.CARD_H / 2
                c.create_oval(cx - 16, cy - 16, cx + 16, cy + 16,
                              outline=SLOT_OUTLINE, width=3)

        # --- waste -------------------------------------------------------
        waste = g.waste.to_list()
        if source and source[0] == "waste":
            waste = waste[:-1]
        shown = waste[-3:] if g.draw_count == 3 else waste[-1:]
        for i, card in enumerate(shown):
            self.draw_card(L.column_x(1) + i * L.WASTE_FAN, L.TOP_Y, card)

        # --- foundations -------------------------------------------------
        for suit in SUITS:
            rect = L.foundation_rect(suit)
            cards = g.foundation[suit].to_list()
            if source and source == ("foundation", suit):
                cards = cards[:-1]
            if cards:
                self.draw_card(rect[0], rect[1], cards[-1])
            else:
                self.draw_slot(rect, SUIT_SYMBOLS[suit])

        # --- tableau -----------------------------------------------------
        for col in range(7):
            cards = g.tableau[col].to_list()
            if source and source[0] == "tableau" and source[1] == col:
                cards = cards[:source[2]]
            if not cards:
                self.draw_slot(L.tableau_slot_rect(col))
                continue
            for card, y in zip(cards, L.card_ys(cards)):
                self.draw_card(L.column_x(col), y, card)

        # --- clickable regions (rebuilt from the real game state) ---------
        self.regions = L.build_regions(g)

        # --- hint outlines -----------------------------------------------
        if self.hint:
            for x1, y1, x2, y2 in L.hint_rects(g, *self.hint):
                self.rounded_rect(x1 - 3, y1 - 3, x2 + 3, y2 + 3, r=10, fill="",
                                  outline=HINT_COLOR, width=4)

        if self.win_shown:
            self.draw_win_banner()

        self.update_stats()

    def draw_win_banner(self):
        c = self.canvas
        c.create_rectangle(0, 0, L.CANVAS_W, L.CANVAS_H, fill="black", stipple="gray50")
        cx, cy = L.CANVAS_W / 2, L.CANVAS_H / 2
        c.create_text(cx, cy - 30, text="YOU WON!", font=(FONT, 56, "bold"),
                      fill=HINT_COLOR)
        g = self.game
        c.create_text(cx, cy + 35, fill="white", font=(FONT, 18),
                      text=f"Score {g.score}   |   {g.move_count} moves   |   {g.elapsed_str()}")

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------
    def on_press(self, event):
        if self.game.is_won():
            return
        self.hint = None
        region = L.hit_test(self.regions, event.x, event.y)
        if region is None:
            return
        if region.kind == "stock":
            self.finish(*self.game.draw())
            return
        cards = L.drag_cards(self.game, region) if region.kind in (
            "waste", "foundation", "tableau") else None
        if not cards:
            return
        x1, y1 = region.rect[0], region.rect[1]
        self.drag = {
            "source": L.drag_source(region),
            "cards": cards,
            "offset": (event.x - x1, event.y - y1),
            "start": (event.x, event.y),
            "last": (event.x, event.y),
        }
        self.redraw()                       # redraw without the picked-up cards
        for i, card in enumerate(cards):    # and draw them following the mouse
            self.draw_card(event.x - self.drag["offset"][0],
                           event.y - self.drag["offset"][1] + i * L.UP_OFFSET,
                           card, tag="drag")

    def on_motion(self, event):
        if not self.drag:
            return
        lx, ly = self.drag["last"]
        self.canvas.move("drag", event.x - lx, event.y - ly)
        self.drag["last"] = (event.x, event.y)

    def on_release(self, event):
        if not self.drag:
            return
        drag, self.drag = self.drag, None
        sx, sy = drag["start"]
        if abs(event.x - sx) + abs(event.y - sy) <= 6:      # just a click
            self.redraw()
            return
        lead_x = event.x - drag["offset"][0] + L.CARD_W / 2
        lead_y = event.y - drag["offset"][1] + L.CARD_H / 2
        target = L.drop_target(lead_x, lead_y)
        self.finish(*L.attempt_drop(self.game, drag["source"], drag["cards"], target))

    def on_double(self, event):
        """Double-click: send the card to the foundation."""
        if self.game.is_won():
            return
        self.drag = None
        region = L.hit_test(self.regions, event.x, event.y)
        if region is None:
            return
        g = self.game
        if region.kind == "stock":
            result = g.draw()
        elif region.kind == "waste":
            result = g.move_waste_to_foundation()
        elif region.kind == "tableau" and region.idx == len(g.tableau[region.col]) - 1:
            result = g.move_tableau_to_foundation(region.col)
        else:
            return
        self.finish(*result)

    # ------------------------------------------------------------------
    # After every action
    # ------------------------------------------------------------------
    def finish(self, ok, message):
        """Show the result of an action, redraw, and check for a win."""
        if ok is not None:
            self.set_status(message, error=not ok)
        self.redraw()
        if self.game.is_won() and not self.win_shown:
            self.win_shown = True
            self.redraw()
            self.root.after(400, self.ask_play_again)

    def ask_play_again(self):
        g = self.game
        again = messagebox.askyesno(
            "You won!",
            f"Congratulations!\n\nScore: {g.score}\nMoves: {g.move_count}\n"
            f"Time: {g.elapsed_str()}\n\nPlay again?")
        if again:
            self.start_new_game()

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def start_new_game(self):
        self.game = Game(draw_count=self.mode_var.get())
        self.drag = None
        self.hint = None
        self.win_shown = False
        self.set_status("New game started. Good luck!")
        self.redraw()

    def _confirm_abandon(self):
        if self.game.move_count == 0 or self.game.is_won():
            return True
        return messagebox.askyesno("New game", "Abandon the current game?")

    def on_new(self):
        if self._confirm_abandon():
            self.start_new_game()

    def on_mode_change(self):
        if self.mode_var.get() == self.game.draw_count:
            return
        if self._confirm_abandon():
            self.start_new_game()
        else:
            self.mode_var.set(self.game.draw_count)      # put the radio button back

    def on_undo(self):
        self.hint = None
        ok, message = self.game.undo()
        self.finish(ok, message)

    def on_redo(self):
        self.hint = None
        ok, message = self.game.redo()
        self.finish(ok, message)

    def on_hint(self):
        if self.game.is_won():
            return
        moves = self.game.get_valid_moves()
        if not moves:
            self.hint = None
            self.set_status("No moves available - try Undo or start a New Game.", error=True)
        else:
            _, kind, args, text = moves[0]
            self.hint = (kind, args)
            self.set_status("Hint: " + text)
        self.redraw()

    def on_auto(self):
        self.hint = None
        moved = self.game.auto_move_to_foundation()
        if moved:
            self.finish(True, f"Moved {moved} card(s) to the foundation.")
        else:
            self.finish(False, "No cards can go to the foundation right now.")


def main():
    parser = argparse.ArgumentParser(description="Klondike Solitaire (GUI)")
    parser.add_argument("--draw", type=int, choices=(1, 3), default=1,
                        help="cards drawn from the stock at a time")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed for a repeatable deal")
    args = parser.parse_args()

    root = tk.Tk()
    SolitaireApp(root, draw_count=args.draw, seed=args.seed)
    root.mainloop()


if __name__ == "__main__":
    main()
