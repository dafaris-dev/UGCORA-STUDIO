from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.deps import require_login_api
from app.services.config_service import get_config
from app.services.gemini_service import test_connection as gemini_test
from app.services.groq_service import test_connection as groq_test
from app.services.nvidia_service import NvidiaService

router = APIRouter()


@router.post("/api/providers/gemini/test", dependencies=[Depends(require_login_api)])
async def test_gemini(db: Session = Depends(get_db)):
    return gemini_test(get_config(db, "GEMINI_API_KEY"),
                        get_config(db, "GEMINI_MODEL", "gemini-2.0-flash"))


@router.post("/api/providers/groq/test", dependencies=[Depends(require_login_api)])
async def test_groq(db: Session = Depends(get_db)):
    return groq_test(get_config(db, "GROQ_API_KEY"),
                     get_config(db, "GROQ_MODEL", "llama-3.3-70b-versatile"))


@router.post("/api/providers/nvidia/test", dependencies=[Depends(require_login_api)])
async def test_nvidia(db: Session = Depends(get_db)):
    svc = NvidiaService(
        get_config(db, "NVIDIA_API_KEY"),
        get_config(db, "NVIDIA_MODEL"),
        get_config(db, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    )
    result = svc.test_connection()
    result["supports_video"] = svc.supports_video()
    return result
