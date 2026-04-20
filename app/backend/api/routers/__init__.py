from .auth import router as auth_router
from .debug import router as debug_router
from .health_check import router as health_router
from .market_stream import router as market_stream_router
from .markets import router as markets_router
from .portfolios import router as portfolios_router
from .users import router as users_router

__all__ = [
	"auth_router",
	"health_router",
	"debug_router",
	"markets_router",
	"portfolios_router",
	"users_router",
	"market_stream_router",
]

