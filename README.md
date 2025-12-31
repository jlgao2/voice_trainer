# Voice Trainer

A CLI tool for voice training practice. Track and improve your speaking voice over time.

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Usage

### Record a new sample

```bash
# Basic recording (10 seconds)
voice record

# Custom duration
voice record --duration 15

# With a practice passage
voice record --passage

# With a specific passage
voice record --passage-id pitch_range_1
```

### Analyze a recording

```bash
voice analyze recording_20240101_120000.wav
voice analyze path/to/file.wav --save
```

### View history and trends

```bash
voice history
voice history --limit 20
```

### Compare two recordings

```bash
voice compare recording1.wav recording2.wav
```

### List practice passages

```bash
voice passages
voice passages --focus pitch
```

### List audio devices

```bash
voice devices
```

## Analysis Metrics

- **Pitch**: Mean, min, max, standard deviation, range
- **Pitch Variability**: Coefficient of variation (monotone vs expressive)
- **Voice Register**: Approximate chest/mixed/head voice percentages
- **Intensity**: Volume consistency and variation
- **Speaking Rate**: Voiced segments per second (proxy for syllable rate)
- **Expressiveness Score**: Composite score (0-100) based on pitch dynamics

## Sample Passages

The tool includes 10 practice passages targeting different aspects:
- Pitch range (questions, emotional contrast)
- Sustained sounds
- Intonation patterns (lists, directions)
- Volume control
- Articulation speed
- Chest resonance
- Head voice brightness
- Mixed expression
