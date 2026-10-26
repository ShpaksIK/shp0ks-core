from fastapi import APIRouter, UploadFile, File, Form
from core.decorators import require_module
from core.services.script_runner import script_runner

router = APIRouter(prefix="/scripts", tags=["scripts"])

@router.get("/list")
@require_module("script_runner")
def list_scripts():
    return script_runner.list_scripts()

@router.post("/run/{name}")
@require_module("script_runner")
def run_existing_script(name: str, as_admin: bool = Form(False)):
    return script_runner.run_existing(name, as_admin)

@router.delete("/delete/{name}")
@require_module("script_runner")
def delete_script(name: str):
    return script_runner.delete_script(name)

@router.delete("/clear")
@require_module("script_runner")
def clear_all_scripts():
    return script_runner.clear_scripts()

@router.post("/upload")
@require_module("script_runner")
async def upload_and_run_script(
    file: UploadFile = File(...),
    as_admin: bool = Form(False),
    execute: bool = Form(True)
):
    if not file.filename.endswith(('.bat', '.cmd', '.ps1')):
        return {"success": False, "error": "неподдерживаемый тип файла"}

    save_result = await script_runner.save_upload(file)
    if not save_result["success"]:
        return save_result

    filename = save_result["filename"]

    if not execute:
        return {"success": True, "message": "Файл загружен без выполнения", "filename": filename}

    return script_runner.run_existing(filename, as_admin=as_admin)