from .audio import router as audio_router
from .common import router as common_router
from .promo import router as promo_router
from .payments import router as payments_router

from aiogram import Router

router = Router()
router.include_router(audio_router)
router.include_router(common_router)
router.include_router(promo_router)
router.include_router(payments_router)