from functools import wraps
from inspect import signature
from database_models.databases_connections import redis as redis_instance, get_async_session
from sqlalchemy.exc import SQLAlchemyError

class Atomic:
    def __init__(self, redis_instance):
        self.redis = redis_instance
        self.shadow_data = {}

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_sig = signature(func)
            bound_args = func_sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            async with get_async_session() as db_session:
                try:
                    # Start PostgreSQL transaction
                    await db_session.begin()

                    # Dynamically extract Redis keys
                    redis_keys = self._extract_redis_keys(bound_args.arguments)

                    # Backup Redis state
                    self.shadow_data = {}
                    for key in redis_keys:
                        await self.redis.watch(key)
                        self.shadow_data[key] = await self.redis.get(key)

                    # Execute the main function logic
                    result = await func(db_session=db_session, redis=self.redis, *args, **bound_args.arguments)

                    # Commit PostgreSQL transaction
                    await db_session.commit()

                    # Commit Redis pipeline (if any operations are queued)
                    pipe = self.redis.pipeline()
                    await pipe.execute()

                    return result

                except (SQLAlchemyError, Exception) as e:
                    # Rollback on error
                    await self.rollback()
                    await db_session.rollback()
                    raise e

                finally:
                    # Unwatch all keys
                    await self.redis.unwatch()

        return wrapper

    def _extract_redis_keys(self, params):
        """Extract potential Redis keys from the function's arguments."""
        redis_keys = []
        for key, value in params.items():
            if isinstance(value, str) and "models." in value:  # Example heuristic for Redis keys
                redis_keys.append(value)
        return redis_keys

    async def rollback(self):
        """Rollback Redis state using the shadow data."""
        async with self.redis.pipeline() as pipe:
            for key, value in self.shadow_data.items():
                if value is None:
                    pipe.delete(key)
                else:
                    pipe.set(key, value)
            await pipe.execute()



atomic = Atomic(redis_instance)
