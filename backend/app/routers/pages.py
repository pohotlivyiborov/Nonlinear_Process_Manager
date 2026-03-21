from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..services.source_service import SourceService
from ..services.simulation_params_service import SimulationParamsService


router = APIRouter(tags=['pages'])


@router.get('/')
async def index():
    sources = SourceService.get_all_sources()
    simulation_params = SimulationParamsService.get_simulation_params()
    response = FileResponse("index.html")