from datetime import datetime, timezone
import pytest
from app.services.queue_engine import QueueEngine


def test_fifo_scoring():
    """Verify FIFO queue sorts strictly by oldest timestamp first."""
    # We instantiate QueueEngine with None since we only call calculate_score (a pure method)
    engine = QueueEngine(db=None, redis_repo=None, event_bus=None)

    t1 = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 11, 10, 5, 0, tzinfo=timezone.utc)

    score1 = engine.calculate_score("FIFO", priority_score=10, created_at=t1)
    score2 = engine.calculate_score("FIFO", priority_score=100, created_at=t2)

    # In FIFO, priority_score shouldn't affect the score. Only timestamp matters.
    # Older timestamp must yield a lower score (so it gets popped first by ZPOPMIN)
    assert score1 < score2


def test_priority_scoring():
    """Verify PRIORITY queue sorts by highest priority first, then oldest timestamp."""
    engine = QueueEngine(db=None, redis_repo=None, event_bus=None)

    # Token A: Priority 100, created at 10:05
    # Token B: Priority 50, created at 10:00
    # Token C: Priority 100, created at 10:00
    t_old = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
    t_new = datetime(2026, 6, 11, 10, 5, 0, tzinfo=timezone.utc)

    score_a = engine.calculate_score("PRIORITY", priority_score=100, created_at=t_new)
    score_b = engine.calculate_score("PRIORITY", priority_score=50, created_at=t_old)
    score_c = engine.calculate_score("PRIORITY", priority_score=100, created_at=t_old)

    # Order of pops (smallest score first):
    # C should be first (highest priority, oldest time)
    # A should be second (highest priority, newer time)
    # B should be third (lower priority, even though it arrived older)
    assert score_c < score_a
    assert score_a < score_b


def test_hybrid_scoring():
    """Verify HYBRID queue sorts by priority buckets (priority // 20) first, then FIFO within each bucket."""
    engine = QueueEngine(db=None, redis_repo=None, event_bus=None)

    t_10_00 = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
    t_10_02 = datetime(2026, 6, 11, 10, 2, 0, tzinfo=timezone.utc)
    t_10_05 = datetime(2026, 6, 11, 10, 5, 0, tzinfo=timezone.utc)

    # Token A: Priority 90 (bucket 4), created at 10:05
    # Token B: Priority 80 (bucket 4), created at 10:00
    # Token C: Priority 100 (bucket 5), created at 10:02
    score_a = engine.calculate_score("HYBRID", priority_score=90, created_at=t_10_05)
    score_b = engine.calculate_score("HYBRID", priority_score=80, created_at=t_10_00)
    score_c = engine.calculate_score("HYBRID", priority_score=100, created_at=t_10_02)

    # C is bucket 5 (score_c should be smallest and pop first)
    # A & B are both in bucket 4 (priority // 20 = 4).
    # Since B has an older timestamp (10:00 vs 10:05), B must pop before A.
    # Thus: score_c < score_b < score_a
    assert score_c < score_b
    assert score_b < score_a
