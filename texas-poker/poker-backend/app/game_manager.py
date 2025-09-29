from typing import Dict, List, Optional
import asyncio
import json
from datetime import datetime
from .poker_logic import Deck, Card, get_best_hand, compare_hands, hand_rank_to_string
from .models import Game, GamePlayer, GameStatus, User, BattleRecord
from sqlalchemy.orm import Session
import random

class PokerGame:
    def __init__(self, game_id: int, db: Session):
        self.game_id = game_id
        self.db = db
        self.deck = Deck()
        self.players: Dict[int, GamePlayer] = {}
        self.active_players: List[int] = []
        self.community_cards: List[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_position = 0
        self.current_turn = 0
        self.round_name = "preflop"
        
    def load_from_db(self):
        game = self.db.query(Game).filter(Game.id == self.game_id).first()
        if not game:
            return False
        
        players = self.db.query(GamePlayer).filter(GamePlayer.game_id == self.game_id).all()
        for player in players:
            self.players[player.position] = player
            if not player.is_folded:
                self.active_players.append(player.position)
        
        if game.community_cards:
            self.community_cards = [Card.from_dict(c) for c in game.community_cards]
        
        self.pot = game.pot
        self.dealer_position = game.dealer_position
        self.current_turn = game.current_turn
        self.round_name = game.current_round
        return True
    
    def start_game(self):
        self.deck = Deck()
        positions = list(self.players.keys())
        
        for pos in positions:
            hole_cards = self.deck.deal(2)
            player = self.players[pos]
            player.hole_cards = [c.to_dict() for c in hole_cards]
            player.is_folded = False
            player.current_bet = 0
            player.total_bet = 0
        
        self.active_players = positions.copy()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.round_name = "preflop"
        
        game = self.db.query(Game).filter(Game.id == self.game_id).first()
        small_blind = game.small_blind
        big_blind = game.big_blind
        
        sb_pos = (self.dealer_position + 1) % len(positions)
        bb_pos = (self.dealer_position + 2) % len(positions)
        
        self.place_bet(positions[sb_pos], small_blind)
        self.place_bet(positions[bb_pos], big_blind)
        
        self.current_turn = (self.dealer_position + 3) % len(positions)
        self.current_bet = big_blind
        
        self.save_to_db()
    
    def place_bet(self, position: int, amount: int):
        player = self.players[position]
        actual_bet = min(amount, player.chips)
        player.chips -= actual_bet
        player.current_bet += actual_bet
        player.total_bet += actual_bet
        self.pot += actual_bet
        
        if player.chips == 0:
            player.is_all_in = True
    
    def player_action(self, position: int, action: str, amount: int = 0) -> Dict:
        if position not in self.active_players:
            return {"success": False, "error": "Not your turn"}
        
        player = self.players[position]
        
        if action == "fold":
            player.is_folded = True
            self.active_players.remove(position)
        elif action == "call":
            call_amount = self.current_bet - player.current_bet
            self.place_bet(position, call_amount)
        elif action == "raise":
            call_amount = self.current_bet - player.current_bet
            total_bet = call_amount + amount
            self.place_bet(position, total_bet)
            self.current_bet = player.current_bet
        elif action == "check":
            if player.current_bet < self.current_bet:
                return {"success": False, "error": "Must call or raise"}
        elif action == "all_in":
            self.place_bet(position, player.chips)
            if player.current_bet > self.current_bet:
                self.current_bet = player.current_bet
        
        self.save_to_db()
        
        if self.is_betting_round_complete():
            self.advance_round()
        else:
            self.current_turn = self.get_next_active_player(position)
        
        return {"success": True}
    
    def is_betting_round_complete(self) -> bool:
        if len(self.active_players) <= 1:
            return True
        
        active_bets = [self.players[p].current_bet for p in self.active_players if not self.players[p].is_all_in]
        return len(set(active_bets)) <= 1
    
    def get_next_active_player(self, current_pos: int) -> int:
        positions = list(self.players.keys())
        current_idx = positions.index(current_pos)
        
        for i in range(1, len(positions) + 1):
            next_idx = (current_idx + i) % len(positions)
            next_pos = positions[next_idx]
            if next_pos in self.active_players and not self.players[next_pos].is_all_in:
                return next_pos
        
        return current_pos
    
    def advance_round(self):
        for pos in self.players:
            self.players[pos].current_bet = 0
        
        self.current_bet = 0
        
        if self.round_name == "preflop":
            self.community_cards = self.deck.deal(3)
            self.round_name = "flop"
        elif self.round_name == "flop":
            self.community_cards.extend(self.deck.deal(1))
            self.round_name = "turn"
        elif self.round_name == "turn":
            self.community_cards.extend(self.deck.deal(1))
            self.round_name = "river"
        elif self.round_name == "river":
            self.determine_winner()
            return
        
        if len(self.active_players) > 0:
            self.current_turn = self.get_next_active_player(self.dealer_position)
        
        self.save_to_db()
    
    def determine_winner(self):
        if len(self.active_players) == 1:
            winner_pos = self.active_players[0]
            self.players[winner_pos].winnings = self.pot
            self.save_battle_records()
            return
        
        player_hands = {}
        for pos in self.active_players:
            player = self.players[pos]
            hole_cards = [Card.from_dict(c) for c in player.hole_cards]
            hand_rank, values, cards = get_best_hand(hole_cards, self.community_cards)
            player_hands[pos] = (hand_rank, values)
            player.final_hand = hand_rank_to_string(hand_rank)
        
        sorted_players = sorted(
            player_hands.items(),
            key=lambda x: (x[1][0].value, x[1][1]),
            reverse=True
        )
        
        winners = [sorted_players[0][0]]
        best_hand = sorted_players[0][1]
        
        for pos, hand in sorted_players[1:]:
            if compare_hands(hand, best_hand) == 0:
                winners.append(pos)
            else:
                break
        
        winnings_per_player = self.pot // len(winners)
        for winner_pos in winners:
            self.players[winner_pos].winnings = winnings_per_player
        
        self.save_battle_records()
    
    def save_battle_records(self):
        game = self.db.query(Game).filter(Game.id == self.game_id).first()
        
        for pos, player in self.players.items():
            record = BattleRecord(
                user_id=player.user_id,
                game_id=self.game_id,
                chips_start=player.chips + player.total_bet,
                chips_end=player.chips + player.winnings,
                profit=player.winnings - player.total_bet,
                position=pos,
                hole_cards=player.hole_cards,
                community_cards=[c.to_dict() for c in self.community_cards],
                final_hand=player.final_hand or "Folded",
                is_winner=player.winnings > 0
            )
            self.db.add(record)
            
            user = self.db.query(User).filter(User.id == player.user_id).first()
            if user:
                user.coins = user.coins + player.winnings - player.total_bet
        
        game.status = GameStatus.FINISHED
        game.ended_at = datetime.utcnow()
        self.db.commit()
    
    def save_to_db(self):
        game = self.db.query(Game).filter(Game.id == self.game_id).first()
        if game:
            game.pot = self.pot
            game.community_cards = [c.to_dict() for c in self.community_cards]
            game.current_round = self.round_name
            game.dealer_position = self.dealer_position
            game.current_turn = self.current_turn
            
            for pos, player in self.players.items():
                db_player = self.db.query(GamePlayer).filter(
                    GamePlayer.game_id == self.game_id,
                    GamePlayer.position == pos
                ).first()
                if db_player:
                    db_player.chips = player.chips
                    db_player.current_bet = player.current_bet
                    db_player.total_bet = player.total_bet
                    db_player.is_folded = player.is_folded
                    db_player.is_all_in = player.is_all_in
                    db_player.hole_cards = player.hole_cards
            
            self.db.commit()

class GameManager:
    def __init__(self):
        self.active_games: Dict[int, PokerGame] = {}
    
    def create_game(self, game_id: int, db: Session) -> PokerGame:
        game = PokerGame(game_id, db)
        self.active_games[game_id] = game
        return game
    
    def get_game(self, game_id: int) -> Optional[PokerGame]:
        return self.active_games.get(game_id)
    
    def remove_game(self, game_id: int):
        if game_id in self.active_games:
            del self.active_games[game_id]

game_manager = GameManager()
