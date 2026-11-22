# Klondike Solitaire - CSC200 Mid Term Project

A text-based Klondike Solitaire game written in Python 3 (no external libraries).

## Run it
```
python phase4.py              # draw 1 card at a time
python phase4.py --draw 3     # draw 3 cards at a time
python phase4.py --seed 42    # repeatable deal
python phase4.py --no-color   # if red suits look odd in your terminal
```

## Run the tests
```
python -m unittest -v
```

## Files (one per project phase)
| File | Phase | What it contains |
|------|-------|------------------|
| `phase1.py` | 1 - Card and Deck | `Card` (suit, rank, face up/down), `Deck` with a Fisher-Yates shuffle |
| `phase2.py` | 2 - Tableau and Foundation | `Stack`, `Queue`, doubly linked-list `TableauPile`, `FoundationPile`, card movement functions |
| `phase3.py` | 3 - Game Logic | `Game`: move validation, stock drawing, card flipping, undo/redo, hints, scoring, timer |
| `phase4.py` | 4 - User Interface | Text interface (run this file) |
| `test_solitaire.py` | Validation & Testing | 41 unit tests |

## Data structures used
| Structure | Where |
|-----------|-------|
| Array / List | The 52-card `Deck` before shuffling and dealing |
| Stack (LIFO) | Four foundation piles, the waste pile, and the undo/redo history |
| Queue (FIFO) | The stockpile - cards are drawn from the front, in order |
| Linked list | The seven tableau columns (bottom card = head, top card = tail) |
| Dictionary | `Game.positions` maps every card to its pile; `Game.foundation` maps suit to pile |

## Commands (columns are 1-7)
| Command | Action |
|---------|--------|
| `d` | draw from the stock (turns the waste over when the stock is empty) |
| `wt <col>` | waste -> tableau column |
| `wf` | waste -> foundation |
| `tf <col>` | top card of a column -> foundation |
| `tt <from> <to> [n]` | move n cards between columns |
| `ft <H/D/C/S> <col>` | foundation -> column |
| `auto` | move every available card to the foundation |
| `h` / `u` / `r` | hint / undo / redo |
| `n` / `q` / `?` | new game / quit / help |

## Rules implemented
- Tableau: build down, alternating colours; only a King goes on an empty column.
- Foundation: build up by suit, Ace to King.
- After a card leaves a column, the new top card is flipped face up.
- You win when all four foundation piles are complete.

## Bonus features
Undo/redo (two stacks), hint system, timer, and scoring
(waste->tableau +5, to foundation +10, flipping a card +5,
foundation->tableau -15, turning the waste over -50).
