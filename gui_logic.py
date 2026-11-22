"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Phase 4 (GUI): board geometry and mouse logic

This module contains everything the graphical interface needs to *decide*
(where is each card, what did the player click, is a drop legal) but nothing
that draws. It does not import tkinter, so it can be unit tested anywhere.
phase4_gui.py is the thin layer that draws the result with tkinter.
"""

from collections import namedtuple

from phase1 import SUITS

# ---------------------------------------------------------------------------
# Layout constants (pixels)
# ---------------------------------------------------------------------------
CARD_W = 80
CARD_H = 112
GAP_X = 20
MARGIN = 24
TOP_Y = 14            # y of the stock / waste / foundation row
TABLEAU_Y = 150       # y of the first card in each tableau column
CANVAS_W = 2 * MARGIN + 7 * CARD_W + 6 * GAP_X
CANVAS_H = 640
DOWN_OFFSET = 14      # vertical gap between face-down cards in a column
UP_OFFSET = 28        # vertical gap between face-up cards in a column
WASTE_FAN = 22        # horizontal gap between waste cards in draw-3 mode

# A clickable area on the board.
#   kind: stock | waste | foundation | foundation_slot | tableau | tableau_empty
Region = namedtuple("Region", "kind rect col idx suit")


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def column_x(col):
    """Left edge of board column 0..6 (the top row uses the same columns)."""
    return MARGIN + col * (CARD_W + GAP_X)


def card_rect(x, y):
    return (x, y, x + CARD_W, y + CARD_H)


def card_ys(cards):
    """Top y of every card in a tableau column, squeezing the column
    together when it would otherwise run off the bottom of the window."""
    if not cards:
        return []
    total = sum(UP_OFFSET if c.face_up else DOWN_OFFSET for c in cards[:-1])
    available = CANVAS_H - TABLEAU_Y - CARD_H - 10
    scale = 1.0 if total <= available or total == 0 else available / total
    ys, y = [], float(TABLEAU_Y)
    for card in cards:
        ys.append(round(y))
        y += (UP_OFFSET if card.face_up else DOWN_OFFSET) * scale
    return ys


def stock_rect():
    return card_rect(column_x(0), TOP_Y)


def foundation_rect(suit):
    return card_rect(column_x(3 + SUITS.index(suit)), TOP_Y)


def waste_shown(game):
    """The waste cards that are visible (1, or up to 3 in draw-3 mode)."""
    cards = game.waste.to_list()
    return cards[-3:] if game.draw_count == 3 else cards[-1:]


def waste_top_rect(game):
    count = len(waste_shown(game))
    return card_rect(column_x(1) + max(0, count - 1) * WASTE_FAN, TOP_Y)


def tableau_slot_rect(col):
    return card_rect(column_x(col), TABLEAU_Y)


def tableau_top_rect(game, col):
    """Rectangle of the top card of a column (or the empty slot)."""
    cards = game.tableau[col].to_list()
    if not cards:
        return tableau_slot_rect(col)
    return card_rect(column_x(col), card_ys(cards)[-1])


# ---------------------------------------------------------------------------
# Regions (what is under the mouse?)
# ---------------------------------------------------------------------------
def build_regions(game):
    """All clickable regions, listed bottom -> top (later = drawn on top)."""
    regions = [Region("stock", stock_rect(), None, None, None)]

    if not game.waste.is_empty():
        regions.append(Region("waste", waste_top_rect(game), None, None, None))

    for suit in SUITS:
        rect = foundation_rect(suit)
        regions.append(Region("foundation_slot", rect, None, None, suit))
        if not game.foundation[suit].is_empty():
            regions.append(Region("foundation", rect, None, None, suit))

    for col in range(7):
        cards = game.tableau[col].to_list()
        if not cards:
            regions.append(Region("tableau_empty", tableau_slot_rect(col),
                                  col, None, None))
            continue
        ys = card_ys(cards)
        x = column_x(col)
        for idx in range(len(cards)):
            bottom = ys[idx + 1] if idx + 1 < len(cards) else ys[idx] + CARD_H
            regions.append(Region("tableau", (x, ys[idx], x + CARD_W, bottom),
                                  col, idx, None))
    return regions


def hit_test(regions, x, y):
    """The top-most region containing the point (None if nothing)."""
    for region in reversed(regions):
        x1, y1, x2, y2 = region.rect
        if x1 <= x < x2 and y1 <= y < y2:
            return region
    return None


def drag_cards(game, region):
    """Cards picked up when the player presses on `region` (None if the
    region can't be dragged)."""
    if region.kind == "waste":
        return [game.waste.peek()]
    if region.kind == "foundation":
        return [game.foundation[region.suit].peek()]
    if region.kind == "tableau":
        cards = game.tableau[region.col].to_list()[region.idx:]
        return cards if cards[0].face_up else None
    return None


def drag_source(region):
    """A small description of where a drag started."""
    if region.kind == "waste":
        return ("waste",)
    if region.kind == "foundation":
        return ("foundation", region.suit)
    return ("tableau", region.col, region.idx)


# ---------------------------------------------------------------------------
# Dropping
# ---------------------------------------------------------------------------
def drop_target(cx, cy):
    """Where did the dragged cards land? (cx, cy) is the centre of the
    first dragged card. Returns ("foundation",), ("tableau", col) or None."""
    if cy < TABLEAU_Y:                                   # top row
        left = column_x(3) - GAP_X
        right = column_x(6) + CARD_W + GAP_X
        return ("foundation",) if left <= cx <= right else None
    pitch = CARD_W + GAP_X
    col = round((cx - MARGIN - CARD_W / 2) / pitch)
    if 0 <= col <= 6:
        centre = column_x(col) + CARD_W / 2
        if abs(cx - centre) <= pitch * 0.75:
            return ("tableau", col)
    return None


def attempt_drop(game, source, cards, target):
    """Try to perform a drag-and-drop. Returns (ok, message).
    ok is None when nothing should happen (dropped back where it came from)."""
    if target is None:
        return False, "Drop the card(s) on a column or on the foundation."

    kind = source[0]
    n = len(cards)

    if target[0] == "foundation":
        if kind == "foundation":
            return None, ""
        if n != 1:
            return False, "Only one card at a time can go to the foundation."
        if kind == "waste":
            return game.move_waste_to_foundation()
        return game.move_tableau_to_foundation(source[1])

    col = target[1]
    if kind == "waste":
        return game.move_waste_to_tableau(col)
    if kind == "foundation":
        return game.move_foundation_to_tableau(source[1], col)
    if col == source[1]:
        return None, ""
    return game.move_tableau_to_tableau(source[1], col, n)


# ---------------------------------------------------------------------------
# Hints
# ---------------------------------------------------------------------------
def hint_rects(game, kind, args):
    """Rectangles to outline for a hint produced by Game.get_valid_moves()."""
    if kind == "DRAW":
        return [stock_rect()]
    if kind == "W2F":
        return [waste_top_rect(game),
                foundation_rect(game.waste.peek().suit)]
    if kind == "W2T":
        return [waste_top_rect(game), tableau_top_rect(game, args[0])]
    if kind == "T2F":
        col = args[0]
        return [tableau_top_rect(game, col),
                foundation_rect(game.tableau[col].peek().suit)]
    if kind == "T2T":
        src, dst, count = args
        cards = game.tableau[src].to_list()
        ys = card_ys(cards)
        x = column_x(src)
        run = (x, ys[len(cards) - count], x + CARD_W, ys[-1] + CARD_H)
        return [run, tableau_top_rect(game, dst)]
    return []
