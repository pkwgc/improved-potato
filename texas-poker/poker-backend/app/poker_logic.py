import random
from typing import List, Tuple, Dict
from enum import Enum

class Suit(str, Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14
}

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        
    def __repr__(self):
        return f"{self.rank}{self.suit}"
    
    def to_dict(self):
        return {"rank": self.rank, "suit": self.suit}
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["rank"], data["suit"])

class Deck:
    def __init__(self):
        self.cards = [
            Card(rank.value, suit.value) 
            for suit in Suit 
            for rank in Rank
        ]
        self.shuffle()
    
    def shuffle(self):
        random.shuffle(self.cards)
    
    def deal(self, num: int = 1) -> List[Card]:
        if len(self.cards) < num:
            raise ValueError("Not enough cards in deck")
        dealt = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt

class HandRank(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

def evaluate_hand(cards: List[Card]) -> Tuple[HandRank, List[int]]:
    if len(cards) < 5:
        return HandRank.HIGH_CARD, []
    
    ranks = sorted([RANK_VALUES[c.rank] for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    
    is_flush = len(set(suits)) == 1
    
    is_straight = False
    straight_high = 0
    if len(set(ranks)) == 5:
        if ranks[0] - ranks[4] == 4:
            is_straight = True
            straight_high = ranks[0]
        elif ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5
    
    counts = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    
    if is_straight and is_flush:
        if straight_high == 14:
            return HandRank.ROYAL_FLUSH, [14]
        return HandRank.STRAIGHT_FLUSH, [straight_high]
    
    if counts[0][1] == 4:
        return HandRank.FOUR_OF_KIND, [counts[0][0], counts[1][0]]
    
    if counts[0][1] == 3 and counts[1][1] == 2:
        return HandRank.FULL_HOUSE, [counts[0][0], counts[1][0]]
    
    if is_flush:
        return HandRank.FLUSH, ranks[:5]
    
    if is_straight:
        return HandRank.STRAIGHT, [straight_high]
    
    if counts[0][1] == 3:
        kickers = [c[0] for c in counts[1:3]]
        return HandRank.THREE_OF_KIND, [counts[0][0]] + kickers
    
    if counts[0][1] == 2 and counts[1][1] == 2:
        return HandRank.TWO_PAIR, [counts[0][0], counts[1][0], counts[2][0]]
    
    if counts[0][1] == 2:
        kickers = [c[0] for c in counts[1:4]]
        return HandRank.PAIR, [counts[0][0]] + kickers
    
    return HandRank.HIGH_CARD, ranks[:5]

def get_best_hand(hole_cards: List[Card], community_cards: List[Card]) -> Tuple[HandRank, List[int], List[Card]]:
    all_cards = hole_cards + community_cards
    if len(all_cards) < 5:
        return HandRank.HIGH_CARD, [], []
    
    from itertools import combinations
    best_rank = HandRank.HIGH_CARD
    best_values = []
    best_cards = []
    
    for combo in combinations(all_cards, 5):
        rank, values = evaluate_hand(list(combo))
        if rank.value > best_rank.value or (rank.value == best_rank.value and values > best_values):
            best_rank = rank
            best_values = values
            best_cards = list(combo)
    
    return best_rank, best_values, best_cards

def compare_hands(hand1: Tuple[HandRank, List[int]], hand2: Tuple[HandRank, List[int]]) -> int:
    rank1, values1 = hand1
    rank2, values2 = hand2
    
    if rank1.value > rank2.value:
        return 1
    elif rank1.value < rank2.value:
        return -1
    else:
        if values1 > values2:
            return 1
        elif values1 < values2:
            return -1
        else:
            return 0

def hand_rank_to_string(rank: HandRank) -> str:
    return {
        HandRank.HIGH_CARD: "High Card",
        HandRank.PAIR: "Pair",
        HandRank.TWO_PAIR: "Two Pair",
        HandRank.THREE_OF_KIND: "Three of a Kind",
        HandRank.STRAIGHT: "Straight",
        HandRank.FLUSH: "Flush",
        HandRank.FULL_HOUSE: "Full House",
        HandRank.FOUR_OF_KIND: "Four of a Kind",
        HandRank.STRAIGHT_FLUSH: "Straight Flush",
        HandRank.ROYAL_FLUSH: "Royal Flush"
    }[rank]
