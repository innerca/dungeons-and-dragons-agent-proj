import { useState, useEffect } from 'react';
import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { CreateCharacter } from './pages/CreateCharacter';
import { getPlayerState } from './services/api';

type AppState = 'loading' | 'login' | 'create_character' | 'game';

function App() {
  const [appState, setAppState] = useState<AppState>(() => {
    const token = localStorage.getItem('token');
    return token ? 'loading' : 'login';
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Check if player has a character
    getPlayerState()
      .then((state) => {
        if (state.error || !state.character_name) {
          setAppState('create_character');
        } else {
          setAppState('game');
        }
      })
      .catch(() => {
        // Token invalid or server down
        localStorage.removeItem('token');
        localStorage.removeItem('player_id');
        setAppState('login');
      });
  }, []);

  const handleAuth = (playerId: string, token: string) => {
    localStorage.setItem('player_id', playerId);
    localStorage.setItem('token', token);
    // Check for existing character
    getPlayerState()
      .then((state) => {
        if (state.error || !state.character_name) {
          setAppState('create_character');
        } else {
          setAppState('game');
        }
      })
      .catch(() => setAppState('create_character'));
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('player_id');
    setAppState('login');
  };

  if (appState === 'loading') {
    return <div className="auth-container"><div className="auth-card"><p>Loading...</p></div></div>;
  }

  if (appState === 'login') {
    return <Login onAuth={handleAuth} />;
  }

  if (appState === 'create_character') {
    return <CreateCharacter onCreated={() => setAppState('game')} />;
  }

  return <Home onLogout={handleLogout} />;
}

export default App;
