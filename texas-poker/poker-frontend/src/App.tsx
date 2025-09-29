import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api, User } from './lib/api';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import LobbyPage from './pages/LobbyPage';
import GamePage from './pages/GamePage';
import ProfilePage from './pages/ProfilePage';
import AdminPage from './pages/AdminPage';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.getCurrentUser()
        .then(setUser)
        .catch(() => {
          api.clearToken();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-green-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading...</div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/lobby" /> : <LoginPage onLogin={setUser} />} />
        <Route path="/register" element={user ? <Navigate to="/lobby" /> : <RegisterPage onRegister={setUser} />} />
        <Route path="/lobby" element={user ? <LobbyPage user={user} /> : <Navigate to="/login" />} />
        <Route path="/game/:gameId" element={user ? <GamePage user={user} /> : <Navigate to="/login" />} />
        <Route path="/profile" element={user ? <ProfilePage user={user} onUpdateUser={setUser} /> : <Navigate to="/login" />} />
        <Route path="/admin" element={user?.role === 'admin' ? <AdminPage user={user} /> : <Navigate to="/lobby" />} />
        <Route path="/" element={<Navigate to={user ? "/lobby" : "/login"} />} />
      </Routes>
    </Router>
  );
}

export default App;
