from aiogram import Router

router = Router()

def setup_routers():
    from .audio import router as audio_router
    from .common import router as common_router
    
    router.include_router(common_router)
    router.include_router(audio_router)
    
    return router