from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager, contextmanager
from redis.asyncio import Redis
from urllib.parse import quote
import asyncio


redis = Redis(
    host='192.168.16.143',
    port=6290,
    db=0,
    password=None,
    socket_timeout=None,
    socket_connect_timeout=1,
    socket_keepalive=True,
    socket_keepalive_options=None,
    encoding='utf-8',
    encoding_errors='strict',
    decode_responses=False,
    retry_on_timeout=True,
    retry_on_error=[ConnectionError],
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    ssl_ca_data=None,
    ssl_check_hostname=False,
    ssl_min_version=None,
    ssl_ciphers=None,
    max_connections=100,
    single_connection_client=False,
    health_check_interval=10,
    client_name='my_redis_client',
    lib_name='redis-py',
    lib_version=None,
    username=None,
    retry=None,
    auto_close_connection_pool=None,
    redis_connect_func=None,
    credential_provider=None,
    protocol=3
)
password="123@"
encoded_password = quote(password)
# Asynchronous PostgreSQL engine with arguments
engine = create_async_engine(
    f'postgresql+asyncpg://rsvpuser:{encoded_password}@localhost:5432/rsvp',
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    max_overflow=10,
    pool_size=5
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
    info=None,
    twophase=False,
    future=True
)


@asynccontextmanager
async def get_async_session():

    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

# For backward compatibility
@contextmanager
def get_sync_session():

    raise NotImplementedError("Synchronous sessions are not supported. Use `get_async_session` instead.")
