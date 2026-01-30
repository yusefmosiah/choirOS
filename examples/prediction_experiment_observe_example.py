"""
Example: Adding a New Feature with PREDICTION/EXPERIMENT/OBSERVE

This is a template showing how to implement a new feature following the pattern.
"""

import unittest
from typing import Optional


class FeatureCache:
    """Example feature: A simple cache with TTL."""

    def __init__(self):
        self._store = {}
        self._timestamps = {}

    def get(self, key: str) -> Optional[str]:
        """Get value if exists and not expired."""
        if key not in self._store:
            return None

        import time
        if time.time() - self._timestamps[key] > 60:  # 60s TTL
            del self._store[key]
            del self._timestamps[key]
            return None

        return self._store[key]

    def set(self, key: str, value: str) -> None:
        """Set value with current timestamp."""
        import time
        self._store[key] = value
        self._timestamps[key] = time.time()


class TestFeatureCache(unittest.TestCase):
    """
    PREDICTION: A simple in-memory cache with 60-second TTL will automatically
    expire stale entries while maintaining fresh data, reducing redundant
    computations.

    EXPERIMENT: Tests verify:
    1. Cache hit returns stored value
    2. Cache miss returns None
    3. Expired entries are automatically evicted
    4. Multiple entries coexist correctly

    OBSERVE: Cache behaves correctly across hit, miss, and expiration scenarios.
    """

    def setUp(self):
        self.cache = FeatureCache()

    def test_cache_hit_returns_stored_value(self):
        """
        PREDICTION: Storing a value and retrieving it immediately returns the
        same value (cache hit).

        EXPERIMENT:
        1. Set key="user:123" to value="alice"
        2. Immediately get key="user:123"
        3. Compare returned value

        OBSERVE:
        - get() returns "alice"
        - Value matches stored value exactly
        """
        self.cache.set("user:123", "alice")
        result = self.cache.get("user:123")

        self.assertEqual(result, "alice")

    def test_cache_miss_returns_none(self):
        """
        PREDICTION: Retrieving a non-existent key returns None (cache miss).

        EXPERIMENT:
        1. Attempt get() on key="user:999" (never set)
        2. Check return value

        OBSERVE:
        - get() returns None
        - No exception raised
        """
        result = self.cache.get("user:999")
        self.assertIsNone(result)

    def test_expired_entry_evicted_on_access(self):
        """
        PREDICTION: Accessing an expired entry triggers automatic eviction and
        returns None.

        EXPERIMENT:
        1. Set key="temp:1" to value="data"
        2. Manually age the entry beyond 60s TTL
        3. Attempt get() on expired key
        4. Verify entry removed from store

        OBSERVE:
        - get() returns None (expired)
        - Key removed from _store dictionary
        - Key removed from _timestamps dictionary
        """
        import time

        self.cache.set("temp:1", "data")

        # Manually expire the entry by setting old timestamp
        self.cache._timestamps["temp:1"] = time.time() - 120  # 2 minutes ago

        result = self.cache.get("temp:1")

        self.assertIsNone(result, "Expired entry should return None")
        self.assertNotIn("temp:1", self.cache._store, "Expired key should be evicted")
        self.assertNotIn("temp:1", self.cache._timestamps, "Timestamp should be removed")

    def test_multiple_entries_independent(self):
        """
        PREDICTION: Multiple cache entries operate independently without
        interference.

        EXPERIMENT:
        1. Set three keys with different values
        2. Retrieve all three
        3. Expire one key
        4. Verify other keys remain accessible

        OBSERVE:
        - All three keys return correct values initially
        - Expired key returns None
        - Other keys still return correct values
        """
        import time

        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")

        # All accessible
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")

        # Expire key2 only
        self.cache._timestamps["key2"] = time.time() - 120

        # key1 and key3 still work, key2 expired
        self.assertEqual(self.cache.get("key1"), "value1", "key1 should still be accessible")
        self.assertIsNone(self.cache.get("key2"), "key2 should be expired")
        self.assertEqual(self.cache.get("key3"), "value3", "key3 should still be accessible")


if __name__ == "__main__":
    unittest.main()


"""
HOW TO USE THIS TEMPLATE:

1. Start with the PREDICTION - What are you trying to achieve?
   "I predict that [feature] will [behavior] because [reason]"

2. Define the EXPERIMENT - How will you test it?
   "I will [action] and observe [result]"

3. Specify OBSERVABLES - How do you know it worked?
   "I expect [specific metrics/assertions]"

4. Implement the feature and test together
   - The test documents the hypothesis
   - The feature implements the experiment
   - The assertions verify the observation

This makes every feature:
- Self-documenting (read the test to understand what it does)
- Verifiable (run the test to prove it works)
- Buildable (extend the hypothesis for new features)

The test isn't separate from the feature. It's part of the feature declaration.
"""
