const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface User {
  id: number;
  username: string;
  email: string;
  nickname: string;
  avatar_url?: string;
  coins: number;
  points: number;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface Game {
  id: number;
  room_id: string;
  status: string;
  max_players: number;
  current_players: number;
  small_blind: number;
  big_blind: number;
  min_buy_in: number;
  pot: number;
  community_cards: any[];
  current_round: string;
}

interface BattleRecord {
  id: number;
  user_id: number;
  game_id: number;
  chips_start: number;
  chips_end: number;
  profit: number;
  hole_cards: any[];
  community_cards: any[];
  final_hand: string;
  is_winner: boolean;
  created_at: string;
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async register(username: string, email: string, password: string, nickname?: string) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, nickname }),
    });
  }

  async login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    return this.request('/api/auth/me');
  }

  async updateProfile(nickname?: string, avatar_url?: string) {
    const params = new URLSearchParams();
    if (nickname) params.append('nickname', nickname);
    if (avatar_url) params.append('avatar_url', avatar_url);
    
    return this.request(`/api/auth/me?${params.toString()}`, {
      method: 'PUT',
    });
  }

  async getGames(status?: string): Promise<Game[]> {
    const params = status ? `?status=${status}` : '';
    return this.request(`/api/games/list${params}`);
  }

  async createGame(data: { max_players: number; small_blind: number; big_blind: number; min_buy_in: number }): Promise<Game> {
    return this.request('/api/games/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async joinGame(gameId: number, buyIn: number) {
    return this.request(`/api/games/join/${gameId}`, {
      method: 'POST',
      body: JSON.stringify({ buy_in: buyIn }),
    });
  }

  async startGame(gameId: number) {
    return this.request(`/api/games/start/${gameId}`, {
      method: 'POST',
    });
  }

  async playerAction(gameId: number, action: string, amount: number = 0) {
    return this.request(`/api/games/action/${gameId}`, {
      method: 'POST',
      body: JSON.stringify({ action, amount }),
    });
  }

  async getGame(gameId: number): Promise<Game> {
    return this.request(`/api/games/${gameId}`);
  }

  async useProp(propType: string, gameId: number, targetPlayerId?: number) {
    return this.request('/api/props/use', {
      method: 'POST',
      body: JSON.stringify({
        prop_type: propType,
        game_id: gameId,
        target_player_id: targetPlayerId,
      }),
    });
  }

  async getPropHistory() {
    return this.request('/api/props/history');
  }

  async getBattleRecords(skip: number = 0, limit: number = 50): Promise<BattleRecord[]> {
    return this.request(`/api/profile/battle-records?skip=${skip}&limit=${limit}`);
  }

  async getUserStatistics() {
    return this.request('/api/profile/statistics');
  }

  async dailySignin() {
    return this.request('/api/profile/daily-signin', {
      method: 'POST',
    });
  }

  async getAdminUsers(skip: number = 0, limit: number = 100) {
    return this.request(`/api/admin/users?skip=${skip}&limit=${limit}`);
  }

  async updateAdminUser(userId: number, data: any) {
    return this.request(`/api/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getAdminStatistics() {
    return this.request('/api/admin/statistics');
  }

  async getPropUsageStats() {
    return this.request('/api/admin/prop-usage');
  }

  getWebSocketUrl(gameId: number): string {
    const wsProtocol = API_URL.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = API_URL.replace(/^https?:\/\//, '');
    return `${wsProtocol}://${baseUrl}/api/games/ws/${gameId}`;
  }
}

const api = new ApiClient();

export { api };
export type { User, Game, BattleRecord };
