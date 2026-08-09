import asyncio
import os
from typing import List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import UploadFile

from app.analysis import analyze_audio
from app.compatibility import sort_tracks as run_sort
from app.exporters.m3u import build_m3u
from app.exporters.rekordbox_xml import build_rekordbox_xml
from app.importers.rekordbox_xml import parse_rekordbox_xml
from app.importers.serato_crate import parse_serato_crate
from app.models import (
    ExportRequest,
    ImportResponse,
    SortRequest,
    SortResponse,
    Track,
    UploadResponse,
)

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac"}

# Individual DJ tracks are usually a few minutes long, but lossless WAV/FLAC
# (or someone uploading a full recorded set) can get big. Default to a
# generous 5GB/track; override with MAX_FILE_SIZE_MB if you want it tighter.
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_MB", "5120")) * 1024 * 1024

# Analysis is CPU-bound (librosa/numpy), so when a batch of tracks is
# uploaded together we run several analyses concurrently on worker threads
# instead of one at a time — the dominant cost during upload. Capped rather
# than unbounded so a big batch doesn't thrash a small/shared-CPU free-tier
# host; override with ANALYSIS_CONCURRENCY if you're on beefier hardware.
ANALYSIS_CONCURRENCY = int(os.environ.get("ANALYSIS_CONCURRENCY", str(min(os.cpu_count() or 2, 4))))

app = FastAPI(
    title="DJ Track Sorter API",
    description=(
        "Upload raw audio or import a Rekordbox XML / Serato crate, and get back "
        "a BPM + Camelot-key-sorted playlist. Nothing is persisted to disk or a "
        "database — uploads are analyzed and discarded."
    ),
    version="0.2.0",
)

# Comma-separated list via env var so the deployed frontend origin (Vercel/
# Netlify) can be added without touching code.
_default_origins = "http://localhost:5173,http://localhost:3000"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


async def _read_multipart_files(request: Request) -> List[UploadFile]:
    """Parse a multipart form with no artificial per-request file-count cap.

    FastAPI's usual `files: List[UploadFile] = File(...)` goes through
    Starlette's default `request.form()`, which caps multipart requests at
    1000 files/fields as a DoS guard. DJs should be able to queue an entire
    library, so we parse the form ourselves with that cap lifted.
    """
    form = await request.form(
        max_files=float("inf"),
        max_fields=float("inf"),
        max_part_size=8 * 1024 * 1024,
    )
    # form.values() collapses repeated field names down to the last one —
    # multi_items() is required to get every file sent under the shared
    # "files" field name.
    return [value for _, value in form.multi_items() if isinstance(value, UploadFile)]


@app.post("/api/upload", response_model=UploadResponse)
async def upload_tracks(request: Request):
    """Accept raw audio files, analyze each for BPM/key, and return them.

    Validation (extension/size) runs first, sequentially, so a bad file
    fails fast. Analysis itself is CPU-bound, so once files are validated we
    run up to ANALYSIS_CONCURRENCY of them at the same time on worker
    threads instead of one at a time — the main lever on wall-clock upload
    time for multi-track batches.
    """
    files = await _read_multipart_files(request)
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    for upload in files:
        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type '{ext}' for '{upload.filename}'. "
                    f"Allowed types: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}."
                ),
            )

        upload.file.seek(0, os.SEEK_END)
        size_bytes = upload.file.tell()
        upload.file.seek(0)

        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"'{upload.filename}' exceeds the "
                    f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB upload limit."
                ),
            )

    semaphore = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

    async def _analyze_one(upload: UploadFile) -> Track:
        try:
            async with semaphore:
                analysis = await asyncio.to_thread(analyze_audio, upload.file, upload.filename)
        except Exception as exc:  # noqa: BLE001 - surface the real decode error to the DJ
            raise HTTPException(
                status_code=422,
                detail=f"Couldn't analyze '{upload.filename}': {exc}",
            ) from exc
        finally:
            await upload.close()

        return Track(
            id=str(uuid4()),
            filename=upload.filename,
            title=os.path.splitext(upload.filename)[0],
            source="analyzed",
            needs_analysis=False,
            **analysis,
        )

    results = await asyncio.gather(*(_analyze_one(upload) for upload in files))
    return UploadResponse(tracks=list(results))


@app.post("/api/import/rekordbox", response_model=ImportResponse)
async def import_rekordbox(request: Request):
    files = await _read_multipart_files(request)
    if not files:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    upload = files[0]
    contents = await upload.read()
    await upload.close()

    try:
        tracks = parse_rekordbox_xml(contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ImportResponse(tracks=tracks)


@app.post("/api/import/serato", response_model=ImportResponse)
async def import_serato(request: Request):
    files = await _read_multipart_files(request)
    if not files:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    upload = files[0]
    contents = await upload.read()
    await upload.close()

    try:
        tracks = parse_serato_crate(contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ImportResponse(tracks=tracks)


@app.post("/api/sort", response_model=SortResponse)
def sort_playlist(body: SortRequest):
    ordered, transitions = run_sort(body.tracks)
    return SortResponse(tracks=ordered, transitions=transitions)


@app.post("/api/export/rekordbox")
def export_rekordbox(body: ExportRequest):
    if not body.tracks:
        raise HTTPException(status_code=400, detail="No tracks to export.")

    xml_bytes = build_rekordbox_xml(body.tracks, playlist_name=body.playlist_name)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="dj-track-sorter-playlist.xml"'},
    )


@app.post("/api/export/m3u")
def export_m3u(body: ExportRequest):
    if not body.tracks:
        raise HTTPException(status_code=400, detail="No tracks to export.")

    m3u_text = build_m3u(body.tracks)
    return Response(
        content=m3u_text,
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": 'attachment; filename="dj-track-sorter-playlist.m3u"'},
    )
