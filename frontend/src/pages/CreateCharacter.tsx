import { useState } from 'react';
import { createCharacter } from '../services/api';

interface Props {
  onCreated: () => void;
}

const BASE_STAT = 10;
const FREE_POINTS = 10;

export function CreateCharacter({ onCreated }: Props) {
  const [name, setName] = useState('');
  const [stats, setStats] = useState({ str: 10, agi: 10, vit: 10, int: 10, dex: 10, luk: 10 });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const usedPoints = Object.values(stats).reduce((sum, v) => sum + (v - BASE_STAT), 0);
  const remaining = FREE_POINTS - usedPoints;

  const adjustStat = (key: keyof typeof stats, delta: number) => {
    setStats((prev) => {
      const newVal = prev[key] + delta;
      if (newVal < 1 || newVal > 30) return prev;
      const newUsed = usedPoints + delta;
      if (newUsed > FREE_POINTS) return prev;
      return { ...prev, [key]: newVal };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setError('Please enter a character name'); return; }
    if (remaining !== 0) { setError(`Please allocate all ${FREE_POINTS} points`); return; }

    setError('');
    setLoading(true);
    try {
      const resp = await createCharacter(name, stats);
      if (resp.error) {
        setError(resp.error);
      } else {
        onCreated();
      }
    } catch {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const statLabels: Record<string, string> = {
    str: 'STR (Strength)',
    agi: 'AGI (Agility)',
    vit: 'VIT (Vitality)',
    int: 'INT (Intelligence)',
    dex: 'DEX (Dexterity)',
    luk: 'LUK (Luck)',
  };

  return (
    <div className="auth-container">
      <div className="auth-card create-char">
        <h1 className="auth-title">Create Character</h1>
        <p className="auth-subtitle">Allocate {FREE_POINTS} bonus points (remaining: {remaining})</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Character Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />

          <div className="stat-grid">
            {(Object.keys(stats) as Array<keyof typeof stats>).map((key) => (
              <div key={key} className="stat-row">
                <span className="stat-label">{statLabels[key]}</span>
                <div className="stat-controls">
                  <button type="button" onClick={() => adjustStat(key, -1)} disabled={stats[key] <= 1}>-</button>
                  <span className="stat-value">{stats[key]}</span>
                  <button type="button" onClick={() => adjustStat(key, 1)} disabled={remaining <= 0 || stats[key] >= 30}>+</button>
                </div>
              </div>
            ))}
          </div>

          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={loading || remaining !== 0}>
            {loading ? '...' : 'Enter Aincrad'}
          </button>
        </form>
      </div>
    </div>
  );
}
