import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, User } from '../lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Users, TrendingUp, DollarSign, Activity } from 'lucide-react';

interface AdminPageProps {
  user: User;
}

export default function AdminPage({}: AdminPageProps) {
  const navigate = useNavigate();
  const [statistics, setStatistics] = useState<any>(null);
  const [propStats, setPropStats] = useState<any>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editCoins, setEditCoins] = useState('');
  const [editWinRate, setEditWinRate] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [stats, props, userList] = await Promise.all([
          api.getAdminStatistics(),
          api.getPropUsageStats(),
          api.getAdminUsers(0, 100),
        ]);
        setStatistics(stats);
        setPropStats(props);
        setUsers(userList);
      } catch (error) {
        console.error('Failed to load admin data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleUpdateUser = async () => {
    if (!selectedUser) return;

    try {
      const updates: any = {};
      if (editCoins) updates.coins = parseInt(editCoins);
      if (editWinRate) updates.win_rate_adjustment = parseFloat(editWinRate);

      await api.updateAdminUser(selectedUser.id, updates);
      alert('User updated successfully!');
      setSelectedUser(null);
      setEditCoins('');
      setEditWinRate('');
      
      const userList = await api.getAdminUsers(0, 100);
      setUsers(userList);
    } catch (error) {
      alert('Failed to update user: ' + error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading admin panel...</div>
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
          <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
          <div></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Users className="text-blue-500" />
                Total Users
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.total_users || 0}</div>
              <div className="text-sm text-gray-600">Active: {statistics?.active_users || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Activity className="text-green-500" />
                Daily Active
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.daily_active_users || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="text-purple-500" />
                Active Games
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.active_games || 0}</div>
              <div className="text-sm text-gray-600">Total: {statistics?.total_games || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <DollarSign className="text-yellow-500" />
                Props Revenue
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{statistics?.total_props_revenue || 0}</div>
              <div className="text-sm text-gray-600">Used: {statistics?.total_props_used || 0}</div>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Props Usage Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">View Others' Cards</div>
                <div className="text-2xl font-bold">{propStats?.view_others_cards || 0} uses</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">View Future Cards</div>
                <div className="text-2xl font-bold">{propStats?.view_future_cards || 0} uses</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>User Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {users.map((u) => (
                <Card key={u.id} className="border">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-bold">{u.username} ({u.nickname})</div>
                        <div className="text-sm text-gray-600">
                          {u.email} | Coins: {u.coins} | Role: {u.role}
                        </div>
                        <div className="text-xs text-gray-500">
                          ID: {u.id} | Active: {u.is_active ? 'Yes' : 'No'}
                        </div>
                      </div>
                      <Button onClick={() => setSelectedUser(u)} size="sm">
                        Edit
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>

        {selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Edit User: {selectedUser.username}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Coins</label>
                  <Input
                    type="number"
                    placeholder={`Current: ${selectedUser.coins}`}
                    value={editCoins}
                    onChange={(e) => setEditCoins(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Win Rate Adjustment (%)</label>
                  <Input
                    type="number"
                    step="0.1"
                    placeholder="Enter adjustment (e.g., 5 for +5%)"
                    value={editWinRate}
                    onChange={(e) => setEditWinRate(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleUpdateUser} className="flex-1">
                    Update
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSelectedUser(null);
                      setEditCoins('');
                      setEditWinRate('');
                    }}
                    className="flex-1"
                  >
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
