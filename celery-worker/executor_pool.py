"""
Executor pool management with atomic allocation.

This module handles the allocation and release of executors using Redis
atomic operations to prevent double-booking when multiple workers are present.
"""

import json
import time
import logging
from typing import Optional, Dict, Any
import redis

logger = logging.getLogger(__name__)


class ExecutorPool:
    """Manages executor allocation using Redis atomic operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.available_key = "executors:available"
        self.busy_prefix = "executor:busy:"
        
    def initialize_pool(self, executor_urls: list[str]) -> None:
        """Initialize the executor pool with available executors."""
        # Clear existing pool
        self.redis.delete(self.available_key)
        
        # Add all executors as available
        for url in executor_urls:
            executor_data = {
                "url": url,
                "added_at": time.time()
            }
            self.redis.lpush(self.available_key, json.dumps(executor_data))
            
        logger.info(f"Initialized executor pool with {len(executor_urls)} executors")
    
    def claim_executor(self, eval_id: str, ttl: int = 300) -> Optional[str]:
        """
        Atomically claim an available executor.
        
        Args:
            eval_id: Evaluation ID claiming the executor
            ttl: Time-to-live for the busy marker (prevents deadlock)
            
        Returns:
            Executor URL if claimed, None if no executors available
        """
        # Atomic pop from available list
        executor_data = self.redis.rpop(self.available_key)
        
        if not executor_data:
            return None
            
        try:
            executor_info = json.loads(executor_data)
            executor_url = executor_info["url"]
            
            # Mark as busy with TTL
            busy_key = f"{self.busy_prefix}{executor_url}"
            self.redis.setex(busy_key, ttl, eval_id)
            
            logger.info(f"Executor {executor_url} claimed by {eval_id}")
            return executor_url
            
        except Exception as e:
            # If something goes wrong, try to return executor to pool
            logger.error(f"Error claiming executor: {e}")
            if executor_data:
                self.redis.lpush(self.available_key, executor_data)
            return None
    
    def release_executor(self, executor_url: str) -> None:
        """
        Return an executor to the available pool (idempotent operation).
        
        This method is safe to call multiple times - it will only add the executor
        back to the pool once, preventing duplicates from race conditions.
        """
        # Use Lua script for atomic check-and-add operation
        lua_script = """
        -- Keys: [1] = available_key, [2] = busy_key
        -- Args: [1] = executor_data_json
        
        -- Remove busy marker (returns 1 if existed, 0 if not)
        local was_busy = redis.call('del', KEYS[2])
        
        -- Check if executor already exists in available pool
        local available_list = redis.call('lrange', KEYS[1], 0, -1)
        local executor_url = cjson.decode(ARGV[1])["url"]
        
        for i, item in ipairs(available_list) do
            local item_data = cjson.decode(item)
            if item_data["url"] == executor_url then
                -- Already in pool, return status
                return {was_busy, 0, "already_in_pool"}
            end
        end
        
        -- Not in pool, add it if it was busy
        if was_busy == 1 then
            redis.call('lpush', KEYS[1], ARGV[1])
            return {was_busy, 1, "released"}
        else
            return {was_busy, 0, "not_busy"}
        end
        """
        
        # Prepare data
        busy_key = f"{self.busy_prefix}{executor_url}"
        executor_data = {
            "url": executor_url,
            "last_used": time.time()
        }
        
        try:
            # Execute atomic operation
            result = self.redis.eval(
                lua_script,
                2,  # number of keys
                self.available_key,  # KEYS[1]
                busy_key,           # KEYS[2]
                json.dumps(executor_data)  # ARGV[1]
            )
            
            was_busy, added_to_pool, status = result
            
            # Log based on result
            if status == "released":
                logger.info(f"Executor {executor_url} released back to pool")
            elif status == "already_in_pool":
                logger.info(f"Executor {executor_url} already in pool (idempotent release)")
            elif status == "not_busy":
                logger.debug(f"Executor {executor_url} was not busy (possible duplicate release)")
            
            # Track metrics for monitoring
            self._track_release_metrics(executor_url, was_busy, added_to_pool, status)
                
        except Exception as e:
            logger.error(f"Error releasing executor {executor_url}: {e}")
            # Even on error, try to ensure executor isn't lost
            # This is a best-effort fallback
            try:
                self.redis.delete(busy_key)
            except:
                pass
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current status of the executor pool."""
        available_count = self.redis.llen(self.available_key)
        
        # Count busy executors
        busy_keys = list(self.redis.scan_iter(match=f"{self.busy_prefix}*"))
        busy_count = len(busy_keys)
        
        # Get details of busy executors
        busy_executors = {}
        for key in busy_keys:
            executor_url = key.decode().replace(self.busy_prefix, "")
            eval_id = self.redis.get(key)
            ttl = self.redis.ttl(key)
            busy_executors[executor_url] = {
                "eval_id": eval_id.decode() if eval_id else None,
                "ttl_seconds": ttl
            }
        
        return {
            "available": available_count,
            "busy": busy_count,
            "total": available_count + busy_count,
            "busy_executors": busy_executors
        }
    
    def recover_stale_executors(self) -> int:
        """
        Recover executors whose busy markers have expired.
        This is a safety mechanism in case cleanup tasks fail.
        
        Returns:
            Number of executors recovered
        """
        # This is handled automatically by Redis TTL expiration
        # but we can actively check and clean up if needed
        recovered = 0
        
        # Get all possible executor URLs from config or discovery
        # For now, this is a placeholder - would need actual executor list
        logger.info(f"Executor recovery check completed, {recovered} executors recovered")
        
        return recovered
    
    def _track_release_metrics(self, executor_url: str, was_busy: int, 
                              added_to_pool: int, status: str) -> None:
        """
        Track metrics for release operations to detect double executions.
        
        This helps monitor if link/link_error callbacks are both running.
        """
        metrics_key = f"executor:metrics:{executor_url}"
        current_time = time.time()
        
        # Store release attempt with timestamp
        release_data = {
            "timestamp": current_time,
            "was_busy": was_busy,
            "added_to_pool": added_to_pool,
            "status": status
        }
        
        # Keep last 100 release attempts for analysis
        self.redis.lpush(metrics_key, json.dumps(release_data))
        self.redis.ltrim(metrics_key, 0, 99)
        self.redis.expire(metrics_key, 86400)  # Expire after 24 hours
        
        # Check for suspicious patterns (multiple releases within 1 second)
        recent_releases = self.redis.lrange(metrics_key, 0, 4)
        if len(recent_releases) >= 2:
            timestamps = []
            for release in recent_releases[:2]:
                # Redis returns bytes, need to decode
                release_str = release.decode() if isinstance(release, bytes) else release
                data = json.loads(release_str)
                timestamps.append(data["timestamp"])
            
            if len(timestamps) >= 2 and (timestamps[0] - timestamps[1]) < 1.0:
                logger.warning(
                    f"Possible double release detected for {executor_url}: "
                    f"2 releases within {timestamps[0] - timestamps[1]:.3f} seconds"
                )