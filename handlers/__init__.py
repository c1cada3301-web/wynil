from aiogram import Router

router = Router()

def setup_routers():
    from .winyl import router as winyl_router
    from .common import router as common_router
    
    router.include_router(common_router)
    router.include_router(winyl_router)

    return router