"""
BabelDOC — FastAPI + Tailwind CSS
"""

import os
import uuid
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

tasks: dict = {}
_lock = threading.Lock()


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def build_translator(engine, api_key, model, base_url, lang_in, lang_out):
    from babeldoc.translator.translator import OpenAITranslator

    defaults = {
        "deepseek": {
            "model": get_env("DEEPSEEK_MODEL", "deepseek-chat"),
            "api_key": get_env("DEEPSEEK_API_KEY"),
            "base_url": get_env(
                "DEEPSEEK_BASE_URL",
                "https://api.deepseek.com",
            ),
        },
        "deepl": {
            "model": "",
            "api_key": get_env("DEEPL_API_KEY"),
            "base_url": get_env("DEEPL_BASE_URL", "https://api.deepl.com"),
        },
        "google": {
            "model": get_env("GOOGLE_MODEL", "gemini-2.0-flash"),
            "api_key": get_env("GOOGLE_API_KEY"),
            "base_url": get_env(
                "GOOGLE_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
        },
    }
    cfg = defaults.get(engine.lower())
    if not cfg:
        raise ValueError(f"unsupported engine: {engine}")
    return OpenAITranslator(
        lang_in=lang_in,
        lang_out=lang_out,
        model=model or cfg["model"],
        api_key=api_key or cfg["api_key"],
        base_url=base_url or cfg["base_url"] or None,
    )


app = FastAPI(title="BabelDOC")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "source_lang": get_env("SOURCE_LANG", "en-US"),
            "target_lang": get_env("TARGET_LANG", "zh-CN"),
            "default_qps": int(get_env("QPS", "4")),
        },
    )


@app.post("/translate")
async def translate(
    files: list[UploadFile] = File(...),
    engine: str = Form("openai"),
    api_key: str = Form(""),
    model: str = Form(""),
    base_url: str = Form(""),
    lang_in: str = Form("en-US"),
    lang_out: str = Form("zh-CN"),
    dual: bool = Form(True),
    mono: bool = Form(True),
    watermark_mode: str = Form("水印版"),
    qps: int = Form(4),
    pages: str = Form(""),
    auto_glossary: bool = Form(True),
):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "progress": 0,
        "status": "starting",
        "results": [],
        "error": None,
    }

    saved = []
    for f in files:
        name = f.filename.strip()
        dest = UPLOAD_DIR / name
        content = await f.read()
        dest.write_bytes(content)
        saved.append(dest)

    t = threading.Thread(
        target=_run_task,
        args=(
            task_id,
            saved,
            engine,
            api_key,
            model,
            base_url,
            lang_in,
            lang_out,
            dual,
            mono,
            watermark_mode,
            qps,
            pages,
            auto_glossary,
        ),
    )
    t.start()
    return {"task_id": task_id}


@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return {"status": "not_found"}
    return task


@app.get("/download/{filename:path}")
async def download(filename: str):
    fp = OUTPUT_DIR / filename
    if not fp.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)
    return FileResponse(str(fp), filename=fp.name)


def _run_task(
    task_id, file_paths, engine, api_key, model, base_url,
    lang_in, lang_out, dual, mono, watermark_mode, qps, pages,
    auto_glossary,
):
    from babeldoc.format.pdf.high_level import translate
    from babeldoc.format.pdf.translation_config import (
        TranslationConfig,
        WatermarkOutputMode,
    )
    from babeldoc.docvision.doclayout import DocLayoutModel

    wm_map = {
        "水印版": WatermarkOutputMode.Watermarked,
        "无水印": WatermarkOutputMode.NoWatermark,
        "两者都输出": WatermarkOutputMode.Both,
    }

    try:
        with _lock:
            tasks[task_id]["status"] = "loading_model"
        doc_layout_model = DocLayoutModel.load_onnx()

        translator = build_translator(
            engine, api_key, model, base_url, lang_in, lang_out
        )

        results = []
        for i, pdf_path in enumerate(file_paths):
            fn = pdf_path.name
            p_base = i / len(file_paths)
            with _lock:
                tasks[task_id]["progress"] = p_base + 0.05
                tasks[task_id]["status"] = f"translating_{i+1}_{len(file_paths)}"

            out_dir = OUTPUT_DIR / pdf_path.stem.strip()
            out_dir.mkdir(exist_ok=True)

            config = TranslationConfig(
                translator=translator,
                input_file=str(pdf_path),
                lang_in=lang_in,
                lang_out=lang_out,
                doc_layout_model=doc_layout_model,
                output_dir=str(out_dir),
                qps=qps,
                pages=pages or None,
                no_dual=not dual,
                no_mono=not mono,
                watermark_output_mode=wm_map[watermark_mode],
                auto_extract_glossary=auto_glossary,
            )

            r = translate(config)
            paths = []
            if r.mono_pdf_path and r.mono_pdf_path.exists():
                paths.append(str(r.mono_pdf_path))
            if r.dual_pdf_path and r.dual_pdf_path.exists():
                paths.append(str(r.dual_pdf_path))
            if (
                r.auto_extracted_glossary_path
                and r.auto_extracted_glossary_path.exists()
            ):
                paths.append(str(r.auto_extracted_glossary_path))
            if (
                r.no_watermark_mono_pdf_path
                and r.no_watermark_mono_pdf_path.exists()
                and str(r.no_watermark_mono_pdf_path) != str(r.mono_pdf_path)
            ):
                paths.append(str(r.no_watermark_mono_pdf_path))
            if (
                r.no_watermark_dual_pdf_path
                and r.no_watermark_dual_pdf_path.exists()
                and str(r.no_watermark_dual_pdf_path) != str(r.dual_pdf_path)
            ):
                paths.append(str(r.no_watermark_dual_pdf_path))
            results.append((fn, paths))

            with _lock:
                tasks[task_id]["progress"] = (i + 1) / len(file_paths) - 0.01

        file_list = []
        for fn, paths in results:
            for p in paths:
                rel = Path(p).relative_to(OUTPUT_DIR)
                file_list.append({"name": Path(p).name, "path": rel.as_posix()})

        with _lock:
            tasks[task_id]["progress"] = 1.0
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["results"] = file_list

    except Exception as e:
        with _lock:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7860)
