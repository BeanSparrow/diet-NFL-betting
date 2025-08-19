# Testing and Development Scripts

This directory contains utility scripts for testing, development, and simulation of the NFL betting system.

## 🎮 Simulation Scripts

### `simulate_betting.py`
Automated betting simulation that:
- Places random bets on upcoming games
- Completes games with random results
- Runs settlement service automatically
- Shows updated leaderboard with real settlement data

**Usage:**
```bash
python scripts/simulate_betting.py
```

### `manual_betting.py`
Interactive manual betting control with menu-driven interface:
- List users and games
- Place specific bets
- Complete games with exact scores
- Run settlement manually
- View pending bets

**Usage:**
```bash
python scripts/manual_betting.py
```

## 📊 Data Management Scripts

### `add_upcoming_games.py`
Adds upcoming NFL games for testing:
- Preseason Week 4 games
- Regular Season Week 1 games
- Extra test games
- Updates existing games to correct season type

**Usage:**
```bash
python scripts/add_upcoming_games.py
```

### `show_betting_options.py`
Quick overview of current system status:
- Available upcoming games
- Users ready to bet
- Recent settlements
- Quick start options

**Usage:**
```bash
python scripts/show_betting_options.py
```

## 🔧 Development Workflow

1. **Initialize with test data:**
   ```bash
   python seed_test_data.py
   ```

2. **Add upcoming games:**
   ```bash
   python scripts/add_upcoming_games.py
   ```

3. **Check status:**
   ```bash
   python scripts/show_betting_options.py
   ```

4. **Run automated simulation:**
   ```bash
   python scripts/simulate_betting.py
   ```

5. **Manual testing (optional):**
   ```bash
   python scripts/manual_betting.py
   ```

## 📝 Notes

- All scripts use the development configuration by default
- Scripts handle Unicode encoding issues for Windows compatibility
- Settlement service integration is fully functional
- Real transaction logging and leaderboard updates