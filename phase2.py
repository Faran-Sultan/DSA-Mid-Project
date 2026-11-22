"""
CSC200 - Data Structures & Algorithms | Mid Term Project
Phase 2: Tableau and Foundation

Data structures built here (all written by hand for the project):

    Stack           (LIFO)        -> foundation piles and the waste pile
    Queue           (FIFO)        -> the stockpile (draw pile)
    TableauPile     (doubly       -> the 7 tableau columns; bottom card = head,
                     linked list)    top (playable) card = tail
    FoundationPile  (a Stack)     -> one pile per suit, built Ace -> King

It also contains the low-level "card movement" functions. These only move
cards around; they do NOT check the Solitaire rules - that is Phase 3.
"""

from collections import deque


# ---------------------------------------------------------------------------
# Stack (LIFO)
# ---------------------------------------------------------------------------
class Stack:
    """Last-In-First-Out. The top of the stack is the end of the list."""

    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        """Look at the top item without removing it (None if empty)."""
        return self._items[-1] if self._items else None

    def is_empty(self):
        return not self._items

    def clear(self):
        self._items.clear()

    def to_list(self):
        """Copy of the items, bottom -> top."""
        return list(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)


# ---------------------------------------------------------------------------
# Queue (FIFO)
# ---------------------------------------------------------------------------
class Queue:
    """First-In-First-Out, used for the stockpile.

    Cards are dequeued from the front (the next card to draw). A deque gives
    O(1) operations at both ends.  `enqueue_front` is only used by undo, to
    put a drawn card back exactly where it was.
    """

    def __init__(self):
        self._items = deque()

    def enqueue(self, item):
        self._items.append(item)

    def enqueue_front(self, item):
        self._items.appendleft(item)

    def dequeue(self):
        if not self._items:
            raise IndexError("dequeue from empty queue")
        return self._items.popleft()

    def peek(self):
        return self._items[0] if self._items else None

    def is_empty(self):
        return not self._items

    def to_list(self):
        """Copy of the items, front -> back."""
        return list(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)


# ---------------------------------------------------------------------------
# Doubly linked list (tableau column)
# ---------------------------------------------------------------------------
class CardNode:
    """One node of the linked list: a card plus links to its neighbours."""

    def __init__(self, card):
        self.card = card
        self.prev = None   # node below this card (towards the bottom)
        self.next = None   # node above this card (towards the top)


class TableauPile:
    """A tableau column stored as a doubly linked list.

    head = bottom card of the column, tail = top (playable) card.
    A doubly linked list lets us remove the top card in O(1) and detach a
    whole run of cards in O(k), which is exactly what Solitaire needs.
    """

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    # ----- adding ----------------------------------------------------------
    def append(self, card):
        """Place a card on top of the column."""
        node = CardNode(card)
        if self.tail is None:
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1

    push = append    # same name as Stack so the movement helpers work on both

    def extend(self, cards):
        """Place several cards (given bottom -> top) on top of the column."""
        for card in cards:
            self.append(card)

    # ----- removing --------------------------------------------------------
    def pop(self):
        """Remove and return the top card."""
        if self.tail is None:
            raise IndexError("pop from empty tableau pile")
        node = self.tail
        self.tail = node.prev
        if self.tail is None:
            self.head = None
        else:
            self.tail.next = None
        self._size -= 1
        return node.card

    def pop_n(self, n):
        """Detach the top n cards at once; returns them bottom -> top."""
        first = self._node_from_top(n)
        cards = []
        node = first
        while node is not None:
            cards.append(node.card)
            node = node.next
        before = first.prev
        if before is None:
            self.head = self.tail = None
        else:
            before.next = None
            self.tail = before
        self._size -= n
        return cards

    # ----- looking ---------------------------------------------------------
    def peek(self):
        """Top card (None if the column is empty)."""
        return self.tail.card if self.tail else None

    def top_cards(self, n):
        """The top n cards WITHOUT removing them, bottom -> top."""
        node = self._node_from_top(n)
        cards = []
        while node is not None:
            cards.append(node.card)
            node = node.next
        return cards

    def _node_from_top(self, n):
        if n < 1 or n > self._size:
            raise ValueError(f"cannot take {n} cards from a pile of {self._size}")
        node = self.tail
        for _ in range(n - 1):
            node = node.prev
        return node

    def is_empty(self):
        return self._size == 0

    def to_list(self):
        """All cards, bottom -> top."""
        cards = []
        node = self.head
        while node is not None:
            cards.append(node.card)
            node = node.next
        return cards

    def __len__(self):
        return self._size

    def __iter__(self):
        return iter(self.to_list())


# ---------------------------------------------------------------------------
# Foundation pile (a Stack for one suit)
# ---------------------------------------------------------------------------
class FoundationPile(Stack):
    """One foundation pile: a stack that only accepts its suit, Ace -> King."""

    def __init__(self, suit):
        super().__init__()
        self.suit = suit

    def can_accept(self, card):
        if card.suit != self.suit:
            return False
        top = self.peek()
        if top is None:
            return card.rank == 1            # must start with an Ace
        return card.rank == top.rank + 1     # then 2, 3, ... King

    def is_complete(self):
        return len(self) == 13


# ---------------------------------------------------------------------------
# Card movement functions (no rule checking - see Phase 3)
# ---------------------------------------------------------------------------
def move_card(source, destination):
    """Move the top card of `source` onto `destination` (any pile type)."""
    destination.push(source.pop())


def move_run(source, destination, count):
    """Move the top `count` cards of one tableau pile onto another,
    keeping their order."""
    destination.extend(source.pop_n(count))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from phase1 import Card

    s = Stack()
    for r in (1, 2, 3):
        s.push(Card("Spades", r))
    print("Stack pops:", [s.pop().rank for _ in range(3)], "(LIFO: 3 2 1)")

    q = Queue()
    for r in (1, 2, 3):
        q.enqueue(Card("Hearts", r))
    print("Queue dequeues:", [q.dequeue().rank for _ in range(3)], "(FIFO: 1 2 3)")

    col = TableauPile()
    col.extend([Card("Clubs", r, True) for r in (9, 8, 7, 6)])
    print("Tableau:", [str(c) for c in col], "-> top is", col.peek())
    moved = col.pop_n(2)
    print("Detached run:", [str(c) for c in moved], "left:", [str(c) for c in col])
