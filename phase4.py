"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Phase 4: Text-based User Interface

Run the game with:
    python phase4.py                 (draw 1 card at a time)
    python phase4.py --draw 3        (draw 3 cards at a time)
    python phase4.py --seed 42       (same deal every time)
    python phase4.py --no-color      (if red suits look odd in your terminal)
"""

import argparse
import os
import sys

from phase1 import SUITS, SUIT_SYMBOLS
from phase3 import Game

SUIT_LETTERS = {"H": "Hearts", "D": "Diamonds", "C": "Clubs", "S": "Spades"}
CELL = 6   # width of one tableau cell

HELP = """
Commands (columns are numbered 1-7):
  d                 draw from the stock (turns the waste over when stock is empty)
  wt <col>          move the top waste card to a tableau column
  wf                move the top waste card to the foundation
  tf <col>          move the top card of a column to the foundation
  tt <from> <to> [n]  move n cards (default 1) from one column to another
  ft <H|D|C|S> <col>  move a foundation card back to a column
  auto              move every available card to the foundation
  h                 hint          u  undo          r  redo
  n                 new game      q  quit          ?  show this help
"""


# ---------------------------------------------------------------------------
# Drawing the board
# ---------------------------------------------------------------------------
def paint(text, card, color):
    """Wrap text in ANSI red for red face-up cards."""
    if color and card is not None and card.face_up and card.color == "Red":
        return f"\033[31m{text}\033[0m"
    return text


def render(game, color=True):
    out = []
    line = "=" * 62
    out.append(line)
    out.append(f" Score: {game.score:<6} Moves: {game.move_count:<5} "
               f"Time: {game.elapsed_str()}    Draw-{game.draw_count}")
    out.append(line)

    # Stock and waste
    stock = f"[##] x{len(game.stock)}" if len(game.stock) else "[  ] empty"
    shown = game.waste.to_list()[-3:] if game.draw_count == 3 else game.waste.to_list()[-1:]
    waste = " ".join(paint(str(c), c, color) for c in shown) if shown else "(empty)"
    out.append(f" Stock: {stock:<14} Waste: {waste}")

    # Foundations
    parts = []
    for suit in SUITS:
        top = game.foundation[suit].peek()
        parts.append(f"{SUIT_SYMBOLS[suit]} " + (paint(str(top), top, color) if top else "--"))
    out.append(" Foundations:  " + "   ".join(parts))
    out.append("")

    # Tableau
    piles = [pile.to_list() for pile in game.tableau]
    out.append("  " + " ".join(str(i + 1).ljust(CELL) for i in range(len(piles))).rstrip())
    height = max(1, max(len(p) for p in piles))
    for row in range(height):
        cells = []
        for pile in piles:
            if row < len(pile):
                card = pile[row]
                text = str(card)
            elif row == 0:
                card, text = None, "[  ]"
            else:
                card, text = None, ""
            cells.append(paint(text, card, color) + " " * (CELL - len(text)))
        out.append("  " + " ".join(cells).rstrip())
    out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Command handling
# ---------------------------------------------------------------------------
def parse_col(text):
    """'3' -> 2 (convert the 1-based number the player types to 0-based)."""
    return int(text) - 1


def handle(game, parts):
    """Run one command. Returns (success, message)."""
    cmd, args = parts[0], parts[1:]

    if cmd == "d":
        return game.draw()
    if cmd == "wf":
        return game.move_waste_to_foundation()
    if cmd == "wt" and len(args) == 1:
        return game.move_waste_to_tableau(parse_col(args[0]))
    if cmd == "tf" and len(args) == 1:
        return game.move_tableau_to_foundation(parse_col(args[0]))
    if cmd == "tt" and len(args) in (2, 3):
        count = int(args[2]) if len(args) == 3 else 1
        return game.move_tableau_to_tableau(parse_col(args[0]), parse_col(args[1]), count)
    if cmd == "ft" and len(args) == 2:
        suit = SUIT_LETTERS.get(args[0].upper())
        if suit is None:
            return False, "Suit must be H, D, C or S."
        return game.move_foundation_to_tableau(suit, parse_col(args[1]))
    if cmd == "auto":
        moved = game.auto_move_to_foundation()
        return (moved > 0), (f"Moved {moved} card(s) to the foundation."
                             if moved else "No cards can go to the foundation.")
    if cmd == "u":
        return game.undo()
    if cmd == "r":
        return game.redo()
    if cmd == "h":
        return True, "Hint: " + game.hint()
    return False, "Unknown command or wrong arguments. Type ? for help."


def play(draw_count, seed, color):
    game = Game(draw_count=draw_count, seed=seed)
    print("\nWelcome to Klondike Solitaire!  Type ? for help.")
    print(render(game, color))

    while True:
        try:
            raw = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return
        if not raw:
            continue
        parts = raw.split()

        if parts[0] in ("q", "quit", "exit"):
            print("Goodbye!")
            return
        if parts[0] in ("?", "help"):
            print(HELP)
            continue
        if parts[0] == "n":
            game = Game(draw_count=draw_count)     # fresh random deal
            print("New game started.")
            print(render(game, color))
            continue

        try:
            ok, message = handle(game, parts)
        except ValueError:
            ok, message = False, "Please enter whole numbers for columns/counts."

        print(("  " if ok else "  ! ") + message)
        print(render(game, color))

        if game.is_won():
            print(f"\n*** YOU WON! ***  Score {game.score}, "
                  f"{game.move_count} moves, time {game.elapsed_str()}")
            try:
                again = input("Play again? (y/n) ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            if again == "y":
                game = Game(draw_count=draw_count)
                print(render(game, color))
            else:
                return


def main():
    parser = argparse.ArgumentParser(description="Klondike Solitaire (text version)")
    parser.add_argument("--draw", type=int, choices=(1, 3), default=1,
                        help="cards drawn from the stock at a time")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed for a repeatable deal")
    parser.add_argument("--no-color", action="store_true",
                        help="turn off coloured (red) suits")
    args = parser.parse_args()

    try:                                   # never crash on unusual consoles
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    if os.name == "nt":
        os.system("")                      # enables ANSI colours on Windows

    play(args.draw, args.seed, color=not args.no_color)


if __name__ == "__main__":
    main()
