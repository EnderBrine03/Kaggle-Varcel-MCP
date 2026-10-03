"""
Kaggle-Varcel-MCP — Full Kaggle API surface via MCP
===================================================
Exposes competitions, datasets, kernels (notebooks), and models to
ChatGPT, Claude, Cursor and other MCP clients.

Transports:
  python server.py          → stdio  (Claude Desktop / Cursor)
  python server.py http     → streamable-http (ChatGPT / Vercel)

Auth (one of):
  KAGGLE_USERNAME + KAGGLE_KEY
  KAGGLE_API_TOKEN
  ~/.kaggle/kaggle.json
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_api():
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as e:
        raise RuntimeError("Install kaggle: pip install kaggle") from e
    api = KaggleApi()
    try:
        api.authenticate()
    except Exception as e:
        raise RuntimeError(
            "Kaggle credentials missing. Set KAGGLE_USERNAME+KAGGLE_KEY "
            "or KAGGLE_API_TOKEN, or place ~/.kaggle/kaggle.json. "
            f"Detail: {e}"
        ) from e
    return api


def _to_json(obj: Any) -> str:
    if obj is None:
        return "null"
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    elif isinstance(obj, list) and obj and hasattr(obj[0], "to_dict"):
        obj = [x.to_dict() for x in obj]
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


def _ok(msg: str, **extra: Any) -> str:
    return json.dumps({"ok": True, "message": msg, **extra}, default=str)


def _err(e: Exception) -> str:
    return json.dumps({"ok": False, "error": str(e)})


mcp = FastMCP(
    "kaggle-varcel-mcp",
    instructions=(
        "Full Kaggle API MCP. Prefer list/search/get tools before download "
        "or submit. Destructive tools (submit, delete, create) require care. "
        "Dataset/competition refs use owner/slug or competition-slug form."
    ),
)


# ===========================================================================
# COMPETITIONS
# ===========================================================================

@mcp.tool()
def competitions_list(
    search: Optional[str] = None,
    group: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "latestDeadline",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """List/search Kaggle competitions.

    Args:
        search: Free-text query.
        group: general | entered | community | hosted | unlaunched.
        category: featured | research | recruitment | gettingStarted | masters | playground | analytics.
        sort_by: grouped | prize | earliestDeadline | latestDeadline | numberOfTeams | recentlyCreated | relevance.
        page: 1-based page.
        page_size: Max 100.
    """
    api = _get_api()
    try:
        comps = api.competitions_list(
            search=search,
            group=group,
            category=category,
            sort_by=sort_by,
            page=page,
            page_size=min(page_size, 100),
        )
        return _to_json(comps)
    except TypeError:
        comps = api.competitions_list(
            search=search, group=group, category=category, sort_by=sort_by, page=page
        )
        return _to_json(comps)
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_get(competition: str) -> str:
    """Get competition metadata by slug (e.g. 'titanic')."""
    api = _get_api()
    try:
        comps = api.competitions_list(search=competition, page=1)
        for c in comps or []:
            ref = getattr(c, "ref", None) or (c.to_dict().get("ref") if hasattr(c, "to_dict") else "")
            if ref and (ref == competition or ref.endswith(competition) or competition in str(ref)):
                return _to_json(c)
        if comps:
            return _to_json(comps[0])
        return json.dumps({"error": f"Competition '{competition}' not found"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_list_files(competition: str) -> str:
    """List data files for a competition (must have accepted rules)."""
    api = _get_api()
    try:
        return _to_json(api.competition_list_files(competition))
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_download_files(
    competition: str,
    path: Optional[str] = None,
    force: bool = False,
) -> str:
    """Download all competition data files to a local path.

    Args:
        competition: Competition slug.
        path: Destination directory (default: ./data/<competition>).
        force: Re-download even if files exist.
    """
    api = _get_api()
    dest = path or str(Path("data") / competition)
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.competition_download_files(competition, path=dest, force=force, quiet=False)
        files = [str(p) for p in Path(dest).rglob("*") if p.is_file()]
        return _ok(f"Downloaded to {dest}", path=dest, files=files[:50], file_count=len(files))
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_download_file(
    competition: str,
    file_name: str,
    path: Optional[str] = None,
    force: bool = False,
) -> str:
    """Download a single competition file.

    Args:
        competition: Competition slug.
        file_name: Exact file name from competition_list_files.
        path: Destination directory.
        force: Overwrite existing.
    """
    api = _get_api()
    dest = path or str(Path("data") / competition)
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.competition_download_file(competition, file_name, path=dest, force=force, quiet=False)
        return _ok(f"Downloaded {file_name}", path=dest, file=file_name)
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_submit(
    competition: str,
    file_name: str,
    message: str = "MCP submission",
) -> str:
    """Submit a prediction file to a competition.

    Args:
        competition: Competition slug.
        file_name: Local path to submission CSV (or required format).
        message: Submission description.
    """
    api = _get_api()
    try:
        result = api.competition_submit(file_name, message, competition)
        return _ok("Submission accepted", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_submissions(competition: str) -> str:
    """List your submissions for a competition."""
    api = _get_api()
    try:
        return _to_json(api.competition_submissions(competition))
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_leaderboard(competition: str) -> str:
    """View public leaderboard (top rows as CSV text)."""
    api = _get_api()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            api.competition_leaderboard_download(competition, path=tmp)
            for root, _, names in os.walk(tmp):
                for n in names:
                    if n.endswith(".csv"):
                        with open(os.path.join(root, n), encoding="utf-8", errors="replace") as f:
                            return "".join(f.readlines()[:51])
            return "Leaderboard downloaded but no CSV found."
    except Exception as e:
        return _err(e)


@mcp.tool()
def competition_leaderboard_download(competition: str, path: Optional[str] = None) -> str:
    """Download full public leaderboard CSV to disk."""
    api = _get_api()
    dest = path or str(Path("data") / competition / "leaderboard")
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.competition_leaderboard_download(competition, path=dest)
        files = list(Path(dest).rglob("*.csv"))
        return _ok("Leaderboard saved", path=dest, files=[str(f) for f in files])
    except Exception as e:
        return _err(e)


# ===========================================================================
# DATASETS
# ===========================================================================

@mcp.tool()
def datasets_list(
    search: Optional[str] = None,
    user: Optional[str] = None,
    sort_by: str = "hottest",
    file_type: Optional[str] = None,
    license_name: Optional[str] = None,
    tag_ids: Optional[str] = None,
    mine: bool = False,
    page: int = 1,
    max_size: Optional[int] = None,
    min_size: Optional[int] = None,
) -> str:
    """Search/list Kaggle datasets.

    Args:
        search: Keywords.
        user: Owner username filter.
        sort_by: hottest | votes | updated | active.
        file_type: csv | json | sqlite | bigQuery | etc.
        license_name: License filter.
        tag_ids: Comma-separated tag ids.
        mine: Only your datasets.
        page: Page number.
        max_size / min_size: Size filters in bytes.
    """
    api = _get_api()
    try:
        kwargs: dict[str, Any] = {
            "search": search,
            "user": user,
            "sort_by": sort_by,
            "file_type": file_type,
            "license_name": license_name,
            "tag_ids": tag_ids,
            "mine": mine,
            "page": page,
        }
        if max_size is not None:
            kwargs["max_size"] = max_size
        if min_size is not None:
            kwargs["min_size"] = min_size
        return _to_json(api.dataset_list(**kwargs))
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_metadata(dataset: str) -> str:
    """Get dataset metadata. Ref: owner/dataset-slug."""
    api = _get_api()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            api.dataset_metadata(dataset, path=tmp)
            meta_path = Path(tmp) / "dataset-metadata.json"
            if meta_path.exists():
                return meta_path.read_text(encoding="utf-8")
            owner, slug = dataset.split("/", 1) if "/" in dataset else ("", dataset)
            results = api.dataset_list(search=slug, user=owner or None, page=1)
            for d in results or []:
                ref = getattr(d, "ref", "") or ""
                if ref == dataset or ref.endswith(dataset):
                    return _to_json(d)
            return json.dumps({"error": f"Metadata for '{dataset}' not found"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_list_files(dataset: str) -> str:
    """List files in a dataset (owner/slug)."""
    api = _get_api()
    try:
        return _to_json(api.dataset_list_files(dataset))
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_status(dataset: str) -> str:
    """Check dataset processing status (owner/slug)."""
    api = _get_api()
    try:
        return _to_json(api.dataset_status(dataset))
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_download_files(
    dataset: str,
    path: Optional[str] = None,
    unzip: bool = True,
    force: bool = False,
) -> str:
    """Download all files of a dataset.

    Args:
        dataset: owner/dataset-slug.
        path: Destination dir (default ./data/<slug>).
        unzip: Unzip after download.
        force: Re-download.
    """
    api = _get_api()
    slug = dataset.split("/")[-1]
    dest = path or str(Path("data") / slug)
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.dataset_download_files(dataset, path=dest, unzip=unzip, force=force, quiet=False)
        files = [str(p) for p in Path(dest).rglob("*") if p.is_file()]
        return _ok(f"Dataset downloaded to {dest}", path=dest, file_count=len(files), files=files[:40])
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_download_file(
    dataset: str,
    file_name: str,
    path: Optional[str] = None,
    force: bool = False,
) -> str:
    """Download a single file from a dataset."""
    api = _get_api()
    slug = dataset.split("/")[-1]
    dest = path or str(Path("data") / slug)
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.dataset_download_file(dataset, file_name, path=dest, force=force, quiet=False)
        return _ok(f"Downloaded {file_name}", path=dest, file=file_name)
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_initialize(folder: str) -> str:
    """Create dataset-metadata.json template in a local folder (for create/version)."""
    api = _get_api()
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        api.dataset_initialize(folder)
        meta = Path(folder) / "dataset-metadata.json"
        return _ok("Initialized", folder=folder, metadata=str(meta), content=meta.read_text() if meta.exists() else None)
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_create(
    folder: str,
    public: bool = False,
    quiet: bool = False,
) -> str:
    """Create a new dataset from a local folder containing dataset-metadata.json + data files.

    Args:
        folder: Path with dataset-metadata.json and files.
        public: Make public (default private).
        quiet: Suppress progress.
    """
    api = _get_api()
    try:
        result = api.dataset_create_new(folder, public=public, quiet=quiet)
        return _ok("Dataset create started", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def dataset_create_version(
    folder: str,
    version_notes: str = "Update via MCP",
    quiet: bool = False,
) -> str:
    """Create a new version of an existing dataset from a local folder."""
    api = _get_api()
    try:
        result = api.dataset_create_version(folder, version_notes, quiet=quiet)
        return _ok("Dataset version create started", result=str(result))
    except Exception as e:
        return _err(e)


# ===========================================================================
# KERNELS (NOTEBOOKS / SCRIPTS)
# ===========================================================================

@mcp.tool()
def kernels_list(
    search: Optional[str] = None,
    user: Optional[str] = None,
    competition: Optional[str] = None,
    dataset: Optional[str] = None,
    parent_kernel: Optional[str] = None,
    language: Optional[str] = None,
    kernel_type: Optional[str] = None,
    output_type: Optional[str] = None,
    sort_by: str = "hotness",
    mine: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Search/list kernels (notebooks & scripts).

    Args:
        search: Free text.
        user: Owner username.
        competition: Competition slug filter.
        dataset: owner/slug filter.
        parent_kernel: Parent kernel ref.
        language: python | r | sqlite | julia.
        kernel_type: script | notebook.
        output_type: Filter by output type.
        sort_by: hotness | commentCount | dateCreated | dateRun | relevance | scoreAscending | scoreDescending | viewCount | voteCount.
        mine: Only your kernels.
        page / page_size: Pagination.
    """
    api = _get_api()
    try:
        kwargs: dict[str, Any] = {
            "search": search,
            "user": user,
            "competition": competition,
            "dataset": dataset,
            "parent_kernel": parent_kernel,
            "language": language,
            "kernel_type": kernel_type,
            "output_type": output_type,
            "sort_by": sort_by,
            "mine": mine,
            "page": page,
        }
        try:
            kwargs["page_size"] = min(page_size, 100)
            return _to_json(api.kernels_list(**kwargs))
        except TypeError:
            kwargs.pop("page_size", None)
            return _to_json(api.kernels_list(**kwargs))
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_list_files(kernel: str) -> str:
    """List files in a kernel. Ref: owner/kernel-slug."""
    api = _get_api()
    try:
        return _to_json(api.kernels_list_files(kernel))
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_pull(
    kernel: str,
    path: Optional[str] = None,
    metadata: bool = True,
) -> str:
    """Download kernel source (and optional metadata) to a local folder.

    Args:
        kernel: owner/kernel-slug.
        path: Destination (default ./kernels/<slug>).
        metadata: Also pull kernel-metadata.json.
    """
    api = _get_api()
    slug = kernel.split("/")[-1]
    dest = path or str(Path("kernels") / slug)
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.kernels_pull(kernel, path=dest, metadata=metadata, quiet=False)
        files = [str(p) for p in Path(dest).rglob("*") if p.is_file()]
        return _ok(f"Kernel pulled to {dest}", path=dest, files=files)
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_push(folder: str) -> str:
    """Push a local kernel folder (with kernel-metadata.json) to Kaggle."""
    api = _get_api()
    try:
        result = api.kernels_push(folder)
        return _ok("Kernel push started", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_output(
    kernel: str,
    path: Optional[str] = None,
) -> str:
    """Download kernel output files.

    Args:
        kernel: owner/kernel-slug.
        path: Destination directory.
    """
    api = _get_api()
    slug = kernel.split("/")[-1]
    dest = path or str(Path("kernels") / slug / "output")
    Path(dest).mkdir(parents=True, exist_ok=True)
    try:
        api.kernels_output(kernel, path=dest, quiet=False)
        files = [str(p) for p in Path(dest).rglob("*") if p.is_file()]
        return _ok("Output downloaded", path=dest, files=files[:40], file_count=len(files))
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_status(kernel: str) -> str:
    """Get kernel execution status. Ref: owner/kernel-slug."""
    api = _get_api()
    try:
        return _to_json(api.kernels_status(kernel))
    except Exception as e:
        return _err(e)


@mcp.tool()
def kernel_initialize(folder: str, kernel_type: str = "notebook") -> str:
    """Initialize kernel-metadata.json in a local folder.

    Args:
        folder: Target directory.
        kernel_type: notebook | script.
    """
    api = _get_api()
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        if hasattr(api, "kernels_initialize"):
            api.kernels_initialize(folder)
        else:
            meta = {
                "id": "username/kernel-slug",
                "title": "New Kernel",
                "code_file": "notebook.ipynb" if kernel_type == "notebook" else "script.py",
                "language": "python",
                "kernel_type": kernel_type,
                "is_private": True,
                "enable_gpu": False,
                "enable_internet": False,
                "dataset_sources": [],
                "competition_sources": [],
                "kernel_sources": [],
            }
            p = Path(folder) / "kernel-metadata.json"
            p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        meta_path = Path(folder) / "kernel-metadata.json"
        return _ok("Initialized", folder=folder, metadata=str(meta_path))
    except Exception as e:
        return _err(e)


# ===========================================================================
# MODELS
# ===========================================================================

@mcp.tool()
def models_list(
    search: Optional[str] = None,
    owner: Optional[str] = None,
    sort_by: str = "hotness",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Search/list Kaggle Models."""
    api = _get_api()
    try:
        if hasattr(api, "model_list"):
            return _to_json(
                api.model_list(search=search, owner=owner, sort_by=sort_by, page=page)
            )
        if hasattr(api, "models_list"):
            return _to_json(
                api.models_list(search=search, owner=owner, sort_by=sort_by, page=page)
            )
        return json.dumps({"error": "model_list not available in this kaggle package version"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_get(model: str) -> str:
    """Get model details. Ref: owner/model-slug."""
    api = _get_api()
    try:
        if hasattr(api, "model_get"):
            return _to_json(api.model_get(model))
        owner, slug = model.split("/", 1) if "/" in model else ("", model)
        results = api.model_list(search=slug, owner=owner or None) if hasattr(api, "model_list") else []
        for m in results or []:
            ref = getattr(m, "ref", "") or ""
            if ref == model or ref.endswith(model):
                return _to_json(m)
        return json.dumps({"error": f"Model '{model}' not found"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_initialize(folder: str) -> str:
    """Create model-metadata.json template in a folder."""
    api = _get_api()
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        if hasattr(api, "model_initialize"):
            api.model_initialize(folder)
        else:
            meta = {
                "ownerSlug": "username",
                "title": "New Model",
                "slug": "new-model",
                "subtitle": "",
                "isPrivate": True,
                "description": {"overview": ""},
                "publishTime": None,
                "provenanceSources": "",
            }
            p = Path(folder) / "model-metadata.json"
            p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return _ok("Model metadata initialized", folder=folder)
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_create(folder: str) -> str:
    """Create a new model from a folder with model-metadata.json."""
    api = _get_api()
    try:
        result = api.model_create_new(folder) if hasattr(api, "model_create_new") else api.model_create(folder)
        return _ok("Model create started", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_update(folder: str) -> str:
    """Update model metadata from a local folder."""
    api = _get_api()
    try:
        result = api.model_update(folder)
        return _ok("Model updated", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_delete(model: str) -> str:
    """Delete a model. Ref: owner/model-slug. DESTRUCTIVE."""
    api = _get_api()
    try:
        result = api.model_delete(model)
        return _ok("Model deleted", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instances_list(model: str) -> str:
    """List instances (framework variants) of a model. Ref: owner/model-slug."""
    api = _get_api()
    try:
        if hasattr(api, "model_instances_list"):
            return _to_json(api.model_instances_list(model))
        if hasattr(api, "model_instance_list"):
            return _to_json(api.model_instance_list(model))
        return json.dumps({"error": "model_instances_list not available"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_get(model_instance: str) -> str:
    """Get a model instance. Ref often: owner/model-slug/framework/instance-slug."""
    api = _get_api()
    try:
        return _to_json(api.model_instance_get(model_instance))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_initialize(folder: str) -> str:
    """Initialize model-instance-metadata.json in a folder."""
    api = _get_api()
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        if hasattr(api, "model_instance_initialize"):
            api.model_instance_initialize(folder)
        else:
            meta = {
                "ownerSlug": "username",
                "modelSlug": "model-slug",
                "instanceSlug": "instance-slug",
                "framework": "pytorch",
                "overview": "",
                "usage": "",
                "licenseName": "Apache 2.0",
                "fineTunable": False,
                "trainingData": [],
                "modelInstanceType": "Unspecified",
            }
            p = Path(folder) / "model-instance-metadata.json"
            p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return _ok("Model instance metadata initialized", folder=folder)
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_create(folder: str) -> str:
    """Create a model instance from a folder with metadata + files."""
    api = _get_api()
    try:
        result = api.model_instance_create(folder)
        return _ok("Model instance create started", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_versions(model_instance: str) -> str:
    """List versions of a model instance."""
    api = _get_api()
    try:
        if hasattr(api, "model_instance_versions"):
            return _to_json(api.model_instance_versions(model_instance))
        if hasattr(api, "model_instance_version_list"):
            return _to_json(api.model_instance_version_list(model_instance))
        return json.dumps({"error": "model_instance_versions not available"})
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_version_create(
    model_instance: str,
    folder: str,
    version_notes: str = "Update via MCP",
) -> str:
    """Create a new version of a model instance from a local folder."""
    api = _get_api()
    try:
        if hasattr(api, "model_instance_version_create"):
            result = api.model_instance_version_create(model_instance, folder, version_notes)
        else:
            result = api.model_instance_create_version(folder, version_notes)
        return _ok("Model instance version create started", result=str(result))
    except Exception as e:
        return _err(e)


@mcp.tool()
def model_instance_files(model_instance: str) -> str:
    """List files for a model instance (or latest version)."""
    api = _get_api()
    try:
        if hasattr(api, "model_instance_files"):
            return _to_json(api.model_instance_files(model_instance))
        return json.dumps({"error": "model_instance_files not available in this package"})
    except Exception as e:
        return _err(e)


# ===========================================================================
# ACCOUNT / UTILITY
# ===========================================================================

@mcp.tool()
def whoami() -> str:
    """Return authenticated Kaggle username (credential check)."""
    api = _get_api()
    username = None
    try:
        username = api.get_config_value("username")
    except Exception:
        pass
    username = username or os.environ.get("KAGGLE_USERNAME") or os.environ.get("KAGGLE_USER")
    return json.dumps({"authenticated": True, "username": username or "(unknown)"})


@mcp.tool()
def config_view() -> str:
    """Show non-secret Kaggle config paths / settings (no API key)."""
    paths = {
        "KAGGLE_CONFIG_DIR": os.environ.get("KAGGLE_CONFIG_DIR"),
        "home_kaggle_json": str(Path.home() / ".kaggle" / "kaggle.json"),
        "home_kaggle_json_exists": (Path.home() / ".kaggle" / "kaggle.json").exists(),
        "KAGGLE_USERNAME_set": bool(os.environ.get("KAGGLE_USERNAME")),
        "KAGGLE_KEY_set": bool(os.environ.get("KAGGLE_KEY")),
        "KAGGLE_API_TOKEN_set": bool(os.environ.get("KAGGLE_API_TOKEN")),
    }
    return json.dumps(paths, indent=2)


# ===========================================================================
# Entrypoint
# ===========================================================================

if __name__ == "__main__":
    import sys

    transport = sys.argv[1].lower() if len(sys.argv) > 1 else "stdio"
    if transport in ("http", "streamable-http", "sse"):
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")
