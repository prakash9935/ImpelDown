"""
Redis Semantic Cache

Caches responses for near-duplicate queries (>0.95 embedding similarity).
24h TTL + event-driven invalidation on document re-ingestion.
"""
