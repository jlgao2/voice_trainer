"""Database module for storing voice analysis results."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json

from .analyzer import VoiceAnalysis


class VoiceDatabase:
    """SQLite database for storing and querying voice analysis results."""

    def __init__(self, db_path: str = "voice_trainer.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL,
                    pitch_mean REAL,
                    pitch_min REAL,
                    pitch_max REAL,
                    pitch_std REAL,
                    pitch_range REAL,
                    pitch_variability_percent REAL,
                    chest_voice_percent REAL,
                    head_voice_percent REAL,
                    mixed_voice_percent REAL,
                    intensity_mean REAL,
                    intensity_std REAL,
                    intensity_min REAL,
                    intensity_max REAL,
                    voiced_fraction REAL,
                    speaking_rate_estimate REAL,
                    expressiveness_score REAL,
                    passage_id TEXT,
                    notes TEXT
                )
            """)
            conn.commit()

    def save_analysis(
        self,
        analysis: VoiceAnalysis,
        passage_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """
        Save an analysis result to the database.

        Returns:
            The ID of the inserted row
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analyses (
                    filename, duration_seconds,
                    pitch_mean, pitch_min, pitch_max, pitch_std, pitch_range,
                    pitch_variability_percent,
                    chest_voice_percent, head_voice_percent, mixed_voice_percent,
                    intensity_mean, intensity_std, intensity_min, intensity_max,
                    voiced_fraction, speaking_rate_estimate, expressiveness_score,
                    passage_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.filename,
                    analysis.duration_seconds,
                    analysis.pitch_mean,
                    analysis.pitch_min,
                    analysis.pitch_max,
                    analysis.pitch_std,
                    analysis.pitch_range,
                    analysis.pitch_variability_percent,
                    analysis.chest_voice_percent,
                    analysis.head_voice_percent,
                    analysis.mixed_voice_percent,
                    analysis.intensity_mean,
                    analysis.intensity_std,
                    analysis.intensity_min,
                    analysis.intensity_max,
                    analysis.voiced_fraction,
                    analysis.speaking_rate_estimate,
                    analysis.expressiveness_score,
                    passage_id,
                    notes,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_analyses(self, limit: int = 50) -> List[dict]:
        """Get all analyses, most recent first."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM analyses
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_analysis_by_id(self, analysis_id: int) -> Optional[dict]:
        """Get a specific analysis by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE id = ?",
                (analysis_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_analysis_by_filename(self, filename: str) -> Optional[dict]:
        """Get analysis by filename."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE filename = ? ORDER BY recorded_at DESC LIMIT 1",
                (filename,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_trends(self, days: int = 14) -> dict:
        """
        Calculate trends over the specified number of days.

        Returns statistics comparing recent performance to earlier performance.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get analyses from the period
            cursor = conn.execute(
                """
                SELECT * FROM analyses
                WHERE recorded_at >= datetime('now', ?)
                ORDER BY recorded_at ASC
                """,
                (f"-{days} days",),
            )
            analyses = [dict(row) for row in cursor.fetchall()]

            if len(analyses) < 2:
                return {"error": "Not enough data for trends", "count": len(analyses)}

            # Split into first half and second half
            mid = len(analyses) // 2
            first_half = analyses[:mid]
            second_half = analyses[mid:]

            metrics = [
                "pitch_mean",
                "pitch_range",
                "pitch_variability_percent",
                "expressiveness_score",
                "intensity_std",
                "speaking_rate_estimate",
            ]

            trends = {"period_days": days, "total_sessions": len(analyses)}

            for metric in metrics:
                first_avg = sum(a[metric] for a in first_half) / len(first_half)
                second_avg = sum(a[metric] for a in second_half) / len(second_half)

                if first_avg != 0:
                    pct_change = ((second_avg - first_avg) / abs(first_avg)) * 100
                else:
                    pct_change = 0

                trends[metric] = {
                    "earlier_avg": round(first_avg, 2),
                    "recent_avg": round(second_avg, 2),
                    "change": round(second_avg - first_avg, 2),
                    "percent_change": round(pct_change, 1),
                }

            return trends

    def get_statistics(self) -> dict:
        """Get overall statistics from all recorded sessions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    AVG(pitch_mean) as avg_pitch_mean,
                    MIN(pitch_min) as lowest_pitch,
                    MAX(pitch_max) as highest_pitch,
                    AVG(pitch_range) as avg_pitch_range,
                    AVG(expressiveness_score) as avg_expressiveness,
                    SUM(duration_seconds) as total_practice_time
                FROM analyses
                """
            )
            row = cursor.fetchone()

            if row[0] == 0:
                return {"error": "No data recorded yet"}

            return {
                "total_sessions": row[0],
                "avg_pitch_mean": round(row[1], 1) if row[1] else 0,
                "lowest_pitch_ever": round(row[2], 1) if row[2] else 0,
                "highest_pitch_ever": round(row[3], 1) if row[3] else 0,
                "avg_pitch_range": round(row[4], 1) if row[4] else 0,
                "avg_expressiveness": round(row[5], 1) if row[5] else 0,
                "total_practice_minutes": round(row[6] / 60, 1) if row[6] else 0,
            }
