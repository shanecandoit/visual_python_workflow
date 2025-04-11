import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CacheManager:
    """Handles in-memory caching of box inputs and outputs."""

    def __init__(self):
        """Initializes the cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("CacheManager initialized.")

    def get_cached_output(self, box_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the cached output data for a given box ID.

        Args:
            box_id: The ID of the box whose cached output is needed.

        Returns:
            The cached output dictionary, or None if not found.
        """
        if box_id in self._cache and 'output' in self._cache[box_id]:
            logger.debug(f"Cache hit for output of box '{box_id}'.")
            return self._cache[box_id]['output']
        else:
            logger.debug(f"Cache miss for output of box '{box_id}'.")
            return None

    def get_cached_inputs(self, box_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the cached input data that led to the cached output for a given box ID.

        Args:
            box_id: The ID of the box whose cached inputs are needed.

        Returns:
            The cached input dictionary, or None if not found or if output wasn't cached.
        """
        if box_id in self._cache and 'inputs' in self._cache[box_id]:
            logger.debug(f"Cache hit for inputs of box '{box_id}'.")
            return self._cache[box_id]['inputs']
        else:
            logger.debug(f"Cache miss for inputs of box '{box_id}'.")
            return None

    def update_cache(self, box_id: str, output_data: Dict[str, Any], input_data: Dict[str, Any]):
        """
        Updates the cache with the output and corresponding inputs for a box.

        Args:
            box_id: The ID of the box to cache data for.
            output_data: The output dictionary from the box execution.
            input_data: The input dictionary used for the execution.
        """
        if not isinstance(output_data, dict) or not isinstance(input_data, dict):
             logger.warning(f"Attempted to update cache for '{box_id}' with non-dict data. Skipping.")
             return

        self._cache[box_id] = {
            'output': output_data,
            'inputs': input_data
        }
        logger.info(f"Updated cache for box '{box_id}' with output keys: {list(output_data.keys())} and input keys: {list(input_data.keys())}")

    def clear_cache(self, box_id: Optional[str] = None):
        """
        Clears the cache for a specific box or for all boxes.

        Args:
            box_id: The ID of the box to clear. If None, clears the entire cache.
        """
        if box_id:
            if box_id in self._cache:
                del self._cache[box_id]
                logger.info(f"Cleared cache for box '{box_id}'.")
            else:
                logger.debug(f"Attempted to clear cache for non-existent box '{box_id}'.")
        else:
            self._cache.clear()
            logger.info("Cleared entire cache.")

    def get_all_cache_keys(self) -> list[str]:
        """Returns a list of all box IDs currently in the cache."""
        return list(self._cache.keys())

if __name__ == '__main__':
    # Example Usage
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    cache = CacheManager()

    # Test cache miss
    print("\n--- Test Cache Miss ---")
    print(f"Output for box_a: {cache.get_cached_output('box_a')}")
    print(f"Inputs for box_a: {cache.get_cached_inputs('box_a')}")

    # Test updating cache
    print("\n--- Test Update Cache ---")
    inputs_a = {'param1': 10}
    outputs_a = {'result_a': 100}
    cache.update_cache('box_a', outputs_a, inputs_a)

    inputs_b = {'param_x': 'hello', 'param_y': True}
    outputs_b = {'result_b': 'world', 'status': 'ok'}
    cache.update_cache('box_b', outputs_b, inputs_b)

    print(f"All cached keys: {cache.get_all_cache_keys()}")

    # Test cache hit
    print("\n--- Test Cache Hit ---")
    print(f"Output for box_a: {cache.get_cached_output('box_a')}")
    print(f"Inputs for box_a: {cache.get_cached_inputs('box_a')}")
    print(f"Output for box_b: {cache.get_cached_output('box_b')}")
    print(f"Inputs for box_b: {cache.get_cached_inputs('box_b')}")

    # Test clearing specific cache
    print("\n--- Test Clear Specific Cache ---")
    cache.clear_cache('box_a')
    print(f"Output for box_a after clear: {cache.get_cached_output('box_a')}")
    print(f"Output for box_b after clear: {cache.get_cached_output('box_b')}")
    print(f"All cached keys: {cache.get_all_cache_keys()}")


    # Test clearing all cache
    print("\n--- Test Clear All Cache ---")
    cache.clear_cache()
    print(f"Output for box_b after clear all: {cache.get_cached_output('box_b')}")
    print(f"All cached keys: {cache.get_all_cache_keys()}")

    # Test updating with non-dict (should warn)
    print("\n--- Test Update with Non-Dict ---")
    cache.update_cache('box_c', ["list"], {"input": 1})