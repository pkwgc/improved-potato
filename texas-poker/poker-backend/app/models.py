from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .database import Base
import enum

class UserRole(str, enum.Enum):
    PLAYER = "player"
    ADMIN = "admin"

class GameStatus(str, enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

class PropType(str, enum.Enum):
    VIEW_OTHERS_CARDS = "view_others_cards"
    VIEW_FUTURE_CARDS = "view_future_cards"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nickname = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    coins = Column(Integer, default=1000)
    points = Column(Integer, default=0)
    role = Column(Enum(UserRole), default=UserRole.PLAYER)
    win_rate_adjustment = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    games_played = relationship("GamePlayer", back_populates="user")
    battle_records = relationship("BattleRecord", back_populates="user")
    prop_usage = relationship("PropUsage", back_populates="user")

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.WAITING)
    max_players = Column(Integer, default=6)
    current_players = Column(Integer, default=0)
    small_blind = Column(Integer, default=10)
    big_blind = Column(Integer, default=20)
    min_buy_in = Column(Integer, default=100)
    pot = Column(Integer, default=0)
    community_cards = Column(JSON, default=[])
    current_round = Column(String, default="preflop")
    dealer_position = Column(Integer, default=0)
    current_turn = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    players = relationship("GamePlayer", back_populates="game")
    battle_record = relationship("BattleRecord", back_populates="game", uselist=False)

class GamePlayer(Base):
    __tablename__ = "game_players"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    position = Column(Integer)
    chips = Column(Integer)
    hole_cards = Column(JSON, default=[])
    current_bet = Column(Integer, default=0)
    total_bet = Column(Integer, default=0)
    is_folded = Column(Boolean, default=False)
    is_all_in = Column(Boolean, default=False)
    final_hand = Column(String, nullable=True)
    winnings = Column(Integer, default=0)
    
    game = relationship("Game", back_populates="players")
    user = relationship("User", back_populates="games_played")

class BattleRecord(Base):
    __tablename__ = "battle_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(Integer, ForeignKey("games.id"))
    chips_start = Column(Integer)
    chips_end = Column(Integer)
    profit = Column(Integer)
    position = Column(Integer)
    hole_cards = Column(JSON)
    community_cards = Column(JSON)
    final_hand = Column(String)
    is_winner = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=90))
    
    user = relationship("User", back_populates="battle_records")
    game = relationship("Game", back_populates="battle_record")

class PropUsage(Base):
    __tablename__ = "prop_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(Integer, ForeignKey("games.id"))
    prop_type = Column(Enum(PropType))
    cost = Column(Integer)
    target_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="prop_usage")

class Club(Base):
    __tablename__ = "clubs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
class DailyTask(Base):
    __tablename__ = "daily_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Column(String)
    completed = Column(Boolean, default=False)
    reward_coins = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)
