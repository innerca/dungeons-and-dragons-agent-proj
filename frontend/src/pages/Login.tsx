import { useState } from 'react';
import { register, login } from '../services/api';

interface Props {
  onAuth: (playerId: string, token: string) => void;
}

export function Login({ onAuth }: Props) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      console.log(`[Login] Attempting ${isRegister ? 'register' : 'login'} for user: ${username}`);
      const resp = isRegister
        ? await register(username, displayName || username, password)
        : await login(username, password);

      console.log(`[Login] Response:`, resp);

      if (resp.error) {
        setError(resp.error);
      } else if (resp.token && resp.player_id) {
        onAuth(resp.player_id, resp.token);
      } else {
        setError('Invalid response from server');
      }
    } catch (err) {
      console.error(`[Login] Error:`, err);
      setError('Connection failed - check console for details');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Sword Art Online</h1>
        <p className="auth-subtitle">Progressive DND</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
          {isRegister && (
            <input
              type="text"
              placeholder="Display Name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? '...' : isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        <button
          className="auth-toggle"
          onClick={() => { setIsRegister(!isRegister); setError(''); }}
        >
          {isRegister ? 'Already have an account? Login' : 'Create new account'}
        </button>
      </div>
    </div>
  );
}
