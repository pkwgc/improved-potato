import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, User, Game } from '../lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Coins, Users, Trophy, LogOut, UserCircle, Shield } from 'lucide-react';

interface LobbyPageProps {
  user: User;
}

export default function LobbyPage({ user }: LobbyPageProps) {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [maxPlayers, setMaxPlayers] = useState(6);
  const [smallBlind, setSmallBlind] = useState(10);
  const [bigBlind, setBigBlind] = useState(20);
  const [minBuyIn, setMinBuyIn] = useState(100);
  const navigate = useNavigate();

  const loadGames = async () => {
    try {
      const gameList = await api.getGames('waiting');
      setGames(gameList);
    } catch (error) {
      console.error('Failed to load games:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGames();
    const interval = setInterval(loadGames, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateGame = async () => {
    try {
      const game = await api.createGame({
        max_players: maxPlayers,
        small_blind: smallBlind,
        big_blind: bigBlind,
        min_buy_in: minBuyIn,
      });
      setShowCreateModal(false);
      await api.joinGame(game.id, minBuyIn);
      navigate(`/game/${game.id}`);
    } catch (error) {
      alert('Failed to create game: ' + error);
    }
  };

  const handleJoinGame = async (gameId: number, minBuyIn: number) => {
    try {
      await api.joinGame(gameId, minBuyIn);
      navigate(`/game/${gameId}`);
    } catch (error) {
      alert('Failed to join game: ' + error);
    }
  };

  const handleDailySignin = async () => {
    try {
      const result = await api.dailySignin();
      alert(`Daily sign-in successful! +${result.reward} coins`);
      window.location.reload();
    } catch (error) {
      alert('Already signed in today or error occurred');
    }
  };

  const handleLogout = () => {
    api.clearToken();
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-4xl font-bold text-white flex items-center gap-2">
            🃏 Texas Poker
          </h1>
          <div className="flex gap-2">
            <Link to="/profile">
              <Button variant="outline" className="flex items-center gap-2">
                <UserCircle size={20} />
                Profile
              </Button>
            </Link>
            {user.role === 'admin' && (
              <Link to="/admin">
                <Button variant="outline" className="flex items-center gap-2">
                  <Shield size={20} />
                  Admin
                </Button>
              </Link>
            )}
            <Button variant="destructive" onClick={handleLogout} className="flex items-center gap-2">
              <LogOut size={20} />
              Logout
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserCircle className="text-blue-600" />
                {user.nickname}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 text-lg">
                <Coins className="text-yellow-500" />
                <span className="font-bold">{user.coins}</span> coins
              </div>
              <div className="flex items-center gap-2 text-lg mt-2">
                <Trophy className="text-purple-500" />
                <span className="font-bold">{user.points}</span> points
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Daily Bonus</CardTitle>
            </CardHeader>
            <CardContent>
              <Button onClick={handleDailySignin} className="w-full">
                Claim Daily Reward (+50 coins)
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <Button onClick={() => setShowCreateModal(true)} className="w-full">
                Create New Game
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users />
              Available Games
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Loading games...</div>
            ) : games.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No games available. Create one to start playing!
              </div>
            ) : (
              <div className="space-y-4">
                {games.map((game) => (
                  <Card key={game.id} className="border-2">
                    <CardContent className="p-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold text-lg">Room {game.room_id}</div>
                          <div className="text-sm text-gray-600">
                            Players: {game.current_players}/{game.max_players}
                          </div>
                          <div className="text-sm text-gray-600">
                            Blinds: {game.small_blind}/{game.big_blind}
                          </div>
                          <div className="text-sm text-gray-600">
                            Min Buy-in: {game.min_buy_in} coins
                          </div>
                        </div>
                        <Button
                          onClick={() => handleJoinGame(game.id, game.min_buy_in)}
                          disabled={game.current_players >= game.max_players}
                        >
                          Join Game
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Create New Game</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Max Players</label>
                  <Input
                    type="number"
                    min="2"
                    max="9"
                    value={maxPlayers}
                    onChange={(e) => setMaxPlayers(parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Small Blind</label>
                  <Input
                    type="number"
                    min="1"
                    value={smallBlind}
                    onChange={(e) => setSmallBlind(parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Big Blind</label>
                  <Input
                    type="number"
                    min="1"
                    value={bigBlind}
                    onChange={(e) => setBigBlind(parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Minimum Buy-in</label>
                  <Input
                    type="number"
                    min="1"
                    value={minBuyIn}
                    onChange={(e) => setMinBuyIn(parseInt(e.target.value))}
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleCreateGame} className="flex-1">
                    Create
                  </Button>
                  <Button variant="outline" onClick={() => setShowCreateModal(false)} className="flex-1">
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
