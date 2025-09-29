import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, User, BattleRecord } from '../lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Trophy, TrendingUp, Coins } from 'lucide-react';

interface ProfilePageProps {
  user: User;
  onUpdateUser: (user: User) => void;
}

export default function ProfilePage({ user }: ProfilePageProps) {
  const navigate = useNavigate();
  const [statistics, setStatistics] = useState<any>(null);
  const [records, setRecords] = useState<BattleRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [stats, battleRecords] = await Promise.all([
          api.getUserStatistics(),
          api.getBattleRecords(0, 50),
        ]);
        setStatistics(stats);
        setRecords(battleRecords);
      } catch (error) {
        console.error('Failed to load profile data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading profile...</div>
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
          <h1 className="text-3xl font-bold text-white">My Profile</h1>
          <div></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Coins className="text-yellow-500" />
                Coins
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{user.coins}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Trophy className="text-purple-500" />
                Total Games
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.total_games || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="text-green-500" />
                Win Rate
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.win_rate || 0}%</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Coins className="text-blue-500" />
                Total Profit
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${(statistics?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {statistics?.total_profit || 0}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Battle Records (Last 50 Games)</CardTitle>
          </CardHeader>
          <CardContent>
            {records.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No battle records yet. Play some games to see your history!
              </div>
            ) : (
              <div className="space-y-2">
                {records.map((record) => (
                  <Card key={record.id} className={`border-l-4 ${record.is_winner ? 'border-green-500' : 'border-red-500'}`}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold">
                            Game #{record.game_id} - {record.is_winner ? '🏆 Won' : '❌ Lost'}
                          </div>
                          <div className="text-sm text-gray-600">
                            {record.final_hand}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(record.created_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-2xl font-bold ${record.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {record.profit >= 0 ? '+' : ''}{record.profit}
                          </div>
                          <div className="text-sm text-gray-600">
                            {record.chips_start} → {record.chips_end}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {statistics && (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Props Usage Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Props Used</div>
                  <div className="text-2xl font-bold">{statistics.props_used}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Total Spent on Props</div>
                  <div className="text-2xl font-bold">{statistics.props_total_cost} coins</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
