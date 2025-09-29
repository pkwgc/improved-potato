import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, User, Game } from '../lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ArrowLeft, Eye } from 'lucide-react';

interface GamePageProps {
  user: User;
}

export default function GamePage({ user }: GamePageProps) {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = useState<Game | null>(null);
  const [loading, setLoading] = useState(true);
  const [propResult, setPropResult] = useState<any>(null);

  useEffect(() => {
    const loadGame = async () => {
      try {
        const gameData = await api.getGame(parseInt(gameId!));
        setGame(gameData);
      } catch (error) {
        console.error('Failed to load game:', error);
      } finally {
        setLoading(false);
      }
    };

    loadGame();
    const interval = setInterval(loadGame, 2000);
    return () => clearInterval(interval);
  }, [gameId]);

  const handleStartGame = async () => {
    try {
      await api.startGame(parseInt(gameId!));
      alert('Game started!');
    } catch (error) {
      alert('Failed to start game: ' + error);
    }
  };

  const handleAction = async (action: string, amount: number = 0) => {
    try {
      await api.playerAction(parseInt(gameId!), action, amount);
    } catch (error) {
      alert('Action failed: ' + error);
    }
  };

  const handleUseProp = async (propType: string, targetPlayerId?: number) => {
    try {
      const result = await api.useProp(propType, parseInt(gameId!), targetPlayerId);
      setPropResult(result);
      alert(`Prop used successfully! Remaining coins: ${result.remaining_coins}`);
    } catch (error) {
      alert('Failed to use prop: ' + error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading game...</div>
      </div>
    );
  }

  if (!game) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 flex items-center justify-center">
        <div className="text-white text-2xl">Game not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <Button variant="outline" onClick={() => navigate('/lobby')}>
            <ArrowLeft className="mr-2" />
            Back to Lobby
          </Button>
          <h1 className="text-3xl font-bold text-white">Room {game.room_id}</h1>
          <div className="text-white">
            Status: <span className="font-bold">{game.status}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <Card className="bg-green-700 border-4 border-yellow-600 min-h-96">
              <CardContent className="p-8">
                <div className="text-center mb-8">
                  <div className="text-3xl font-bold text-white mb-4">
                    Pot: {game.pot} chips
                  </div>
                  <div className="text-xl text-white">
                    Round: {game.current_round}
                  </div>
                </div>

                <div className="flex justify-center gap-2 mb-8">
                  {game.community_cards && game.community_cards.length > 0 ? (
                    game.community_cards.map((card: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-white rounded-lg p-4 text-center min-w-16 shadow-lg"
                      >
                        <div className="text-2xl font-bold">
                          {card.rank}
                          <span className={card.suit === '♥' || card.suit === '♦' ? 'text-red-600' : 'text-black'}>
                            {card.suit}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-white text-xl">No community cards yet</div>
                  )}
                </div>

                <div className="text-center">
                  <div className="text-white text-lg mb-4">
                    Players: {game.current_players}/{game.max_players}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardContent className="p-4">
                <h3 className="font-bold text-lg mb-4">Game Controls</h3>
                {game.status === 'waiting' && (
                  <Button onClick={handleStartGame} className="w-full mb-2">
                    Start Game
                  </Button>
                )}
                {game.status === 'playing' && (
                  <div className="space-y-2">
                    <Button onClick={() => handleAction('call')} className="w-full">
                      Call
                    </Button>
                    <Button onClick={() => handleAction('raise', 20)} className="w-full">
                      Raise 20
                    </Button>
                    <Button onClick={() => handleAction('fold')} variant="destructive" className="w-full">
                      Fold
                    </Button>
                    <Button onClick={() => handleAction('check')} variant="outline" className="w-full">
                      Check
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <Eye /> Props System
                </h3>
                <div className="space-y-2">
                  <Button
                    onClick={() => handleUseProp('view_others_cards', 1)}
                    variant="outline"
                    className="w-full text-sm"
                  >
                    View Others' Cards (100 coins)
                  </Button>
                  <Button
                    onClick={() => handleUseProp('view_future_cards')}
                    variant="outline"
                    className="w-full text-sm"
                  >
                    View Future Card (150 coins)
                  </Button>
                </div>
                {propResult && (
                  <div className="mt-4 p-2 bg-blue-100 rounded text-sm">
                    <div className="font-bold">Prop Result:</div>
                    <pre className="text-xs">{JSON.stringify(propResult.info, null, 2)}</pre>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <h3 className="font-bold text-lg mb-2">Game Info</h3>
                <div className="text-sm space-y-1">
                  <div>Small Blind: {game.small_blind}</div>
                  <div>Big Blind: {game.big_blind}</div>
                  <div>Your Coins: {user.coins}</div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
