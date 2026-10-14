#!/usr/bin/env python3
"""
Скрипт автономной загрузки моделей для MayaRealLowVram (Project Maya).
Полностью воспроизводит логику maya.py:
  1. Скачивает модель в стандартную директорию Project Maya (по умолчанию: ../Maya-data/models/<quant>).
  2. Поддерживает докачку (curl -C -).
  3. Скачивает основные шарды модели (.gguf) и файлы vision-энкодера (mmproj, vocab).
  4. Проверяет SHA-256 контрольные суммы после завершения загрузки.
  5. Поддерживает режим проверки (--dry-run / --check-only) без скачивания файлов.
"""

import sys
import os
import shutil
import argparse
import hashlib
import urllib.request
from pathlib import Path

# Импортируем параметры напрямую из maya.py для 100% совместимости
try:
    import maya
    MODELS = maya.MODELS
    DFLASH = getattr(maya, "DFLASH", None)
    HF_URL_FN = maya.hf_url
    DEFAULT_MODELS_DIR = maya.ROOT.parent / "Maya-data" / "models"
    ROOT_DIR = maya.ROOT
except Exception:
    ROOT_DIR = Path(__file__).resolve().parent
    DEFAULT_MODELS_DIR = ROOT_DIR.parent / "Maya-data" / "models"
    HF_FMT = "https://huggingface.co/{repo}/resolve/{revision}/{path}"
    def HF_URL_FN(repo: str, revision: str, folder: str, file: str) -> str:
        return HF_FMT.format(repo=repo, revision=revision, path=f"{folder}/{file}" if folder else file)
    DFLASH = {
        "repo": "Anbeeld/GLM-5.3-Flash-DFlash2-GGUF",
        "revision": "f3569acb7f9cee95e66d24442d75536eb00ab842",
        "file": "GLM-5.3-Flash-DFlash2-Q4_K_M.gguf",
        "bytes": 697017248,
        "sha256": "4b5d0cae5f963f4b46c65fe3db31198f26b52784cf1808ea83fb8b0d87a8e7a8",
        "license": "CC BY-NC-ND 4.0",
    }
    MODELS = {
        "Maya-S24": {
            "about": "Maya-S24: Q4_K attention, экономит ~1.5 GB VRAM (рекомендуется для 4GB / Low-VRAM)",
            "repo": "peasantsmith/GLM-5.3-Flash-Maya-GGUF", "revision": "main", "folder": "Maya-S24",
            "file": "GLM-5.3-Flash-Maya-S24-IQ2_XXS_S-{i:05d}-of-{n:05d}.gguf", "shards": 3, "download_gb": 94.7,
            "sha256": {
                "GLM-5.3-Flash-Maya-S24-IQ2_XXS_S-00001-of-00003.gguf":
                    ["8ebd5c74bcf65ece2a8699b7b6fd2b8d177f350ed252cee252fdd99b86a0138c",
                     "3dc347757686c1435eae36c4872f5c151191cc5063bc188ce699b97700aae076"],
                "GLM-5.3-Flash-Maya-S24-IQ2_XXS_S-00002-of-00003.gguf":
                    "4bd445da3a0128a9c5b32228c924e0a622aa4a132c7a8dc9a2c207a4beea8e34",
                "GLM-5.3-Flash-Maya-S24-IQ2_XXS_S-00003-of-00003.gguf":
                    "a6fd4e88007ac49b431c7d02be34e43ab7a09224d53a0c52782327613cb41917"},
            "vision": {
                "folder": "vision", "mmproj": "mmproj-GLM-5.3-Flash-F16.gguf", "vocab": "GLM-5.3-Flash-vocab.gguf",
                "download_gb": 1.14,
                "sha256": {
                    "mmproj-GLM-5.3-Flash-F16.gguf": "3627575df16bd152db0f3fd7e488d270b33f3a9e6c7fa3b1b8ac381faafde882",
                    "GLM-5.3-Flash-vocab.gguf": "8f53cb1bd2e631c14ef413e3284735d9e53f3c508d07a6f609e705b487105912"}}
        },
        "Maya-S-v2-IQ2_XXS": {
            "about": "Maya-S (v2): базовый квант IQ2_XXS / Q6_K attention (96.5 GB)",
            "repo": "peasantsmith/GLM-5.3-Flash-Maya-GGUF", "revision": "main", "folder": "Maya-S-v2-IQ2_XXS",
            "file": "GLM-5.3-Flash-Maya-S-v2-IQ2_XXS-{i:05d}-of-{n:05d}.gguf", "shards": 3, "download_gb": 96.5,
            "sha256": {
                "GLM-5.3-Flash-Maya-S-v2-IQ2_XXS-00001-of-00003.gguf":
                    ["e56ef50efd71d81ddf6249e08bd2ef5af96ed348c2b7a004491d46168d0ecaa7",
                     "a507f2b7b25e04624ee55c631d3b281caea7cfffc747e5247970cd5a7ea91b3f"],
                "GLM-5.3-Flash-Maya-S-v2-IQ2_XXS-00002-of-00003.gguf":
                    "2d65d88a69f8dc124c8d24bd33b33161ddab218918b4253ad4f500aeede84df5",
                "GLM-5.3-Flash-Maya-S-v2-IQ2_XXS-00003-of-00003.gguf":
                    "a6a981c4fee7a53d78bdbd97d8f465d48ddf439cf938ff90617f395e0351b5a6"},
            "vision": {
                "folder": "vision", "mmproj": "mmproj-GLM-5.3-Flash-F16.gguf", "vocab": "GLM-5.3-Flash-vocab.gguf",
                "download_gb": 1.14,
                "sha256": {
                    "mmproj-GLM-5.3-Flash-F16.gguf": "3627575df16bd152db0f3fd7e488d270b33f3a9e6c7fa3b1b8ac381faafde882",
                    "GLM-5.3-Flash-vocab.gguf": "8f53cb1bd2e631c14ef413e3284735d9e53f3c508d07a6f609e705b487105912"}}
        }
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def check_url_head(url: str) -> tuple[int, int]:
    """Проверяет доступность URL и возвращает (HTTP статус, размер в байтах)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MayaRealLowVram-Downloader"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            size = int(resp.headers.get("Content-Length", 0))
            return status, size
    except Exception as e:
        return 0, 0


def format_bytes(n: int) -> str:
    if n >= 1024**3:
        return f"{n / (1024**3):.2f} GB"
    elif n >= 1024**2:
        return f"{n / (1024**2):.2f} MB"
    elif n >= 1024:
        return f"{n / 1024:.2f} KB"
    return f"{n} B"


def get_model_items(quant: str, base_dir: Path, with_dflash: bool = False) -> list[dict]:
    """Формирует полный список файлов модели, vision и драфтера для загрузки."""
    m = MODELS[quant]
    items = []
    
    # 1. Основные шарды модели
    target_dir = base_dir / quant
    for i in range(1, m["shards"] + 1):
        filename = m["file"].format(i=i, n=m["shards"])
        url = HF_URL_FN(m["repo"], m["revision"], m["folder"], filename)
        want_sha = m["sha256"].get(filename)
        items.append({
            "name": filename,
            "category": "model_shard",
            "url": url,
            "dest": target_dir / filename,
            "sha256": want_sha
        })
        
    # 2. Файлы vision (mmproj и vocab)
    v = m.get("vision")
    if v:
        v_dir = target_dir / v.get("folder", "vision")
        for k in ("mmproj", "vocab"):
            filename = v[k]
            url = HF_URL_FN(m["repo"], m["revision"], v.get("folder", "vision"), filename)
            want_sha = v.get("sha256", {}).get(filename)
            items.append({
                "name": filename,
                "category": "vision_tower",
                "url": url,
                "dest": v_dir / filename,
                "sha256": want_sha
            })

    # 3. Драфтер DFlash2 (опционально, ~697 MB для ускоренного спекулятивного декодинга sm_80+)
    if with_dflash and DFLASH:
        dflash_dir = base_dir / "GLM-5.3-Flash-DFlash2"
        filename = DFLASH["file"]
        url = HF_URL_FN(DFLASH["repo"], DFLASH["revision"], "", filename)
        want_sha = DFLASH["sha256"]
        items.append({
            "name": filename,
            "category": "dflash2_drafter",
            "url": url,
            "dest": dflash_dir / filename,
            "sha256": want_sha
        })
            
    return items


def main():
    parser = argparse.ArgumentParser(
        description="Хирургически точный скрипт загрузки модели GLM-5.3-Flash для MayaRealLowVram"
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        default="Maya-S24",
        help="Выбор модели: Maya-S24 (рекомендуется для 4GB / Low-VRAM) или Maya-S-v2-IQ2_XXS (по умолчанию: Maya-S24)"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help=f"Директория для хранения моделей (по умолчанию: {DEFAULT_MODELS_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        "--check-only",
        action="store_true",
        help="Только проверка доступности URL, структуры каталогов и свободного места без скачивания"
    )
    parser.add_argument(
        "--verify-checksums",
        action="store_true",
        help="Только проверка целостности и SHA256 контрольных сумм уже скачанных файлов"
    )
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Пропустить загрузку файлов vision (mmproj и vocab)"
    )
    parser.add_argument(
        "--with-dflash",
        action="store_true",
        help="Также скачать DFlash2 драфтер (~697 MB) для ускоренного спекулятивного декодинга (+19-44%% FPS на RTX 30+)"
    )

    args = parser.parse_args()

    quant = args.model
    m_info = MODELS[quant]
    base_dir = Path(args.models_dir).resolve()
    target_dir = base_dir / quant

    print("=" * 70)
    print(" MayaRealLowVram: Автономный менеджер загрузки модели")
    print("=" * 70)
    print(f" Модель:        {quant}")
    print(f" Описание:      {m_info['about']}")
    print(f" Каталог:       {target_dir}")
    print(f" Источник:      https://huggingface.co/{m_info['repo']}")
    extra_gb = 1.14 if not args.no_vision else 0.0
    if args.with_dflash and DFLASH:
        extra_gb += DFLASH["bytes"] / (1024**3)
    print(f" Номинал весов: ~{m_info['download_gb']} GB (файлы модели) + ~{extra_gb:.2f} GB (доп. компоненты)")
    print("=" * 70)

    # Проверка свободного места на диске
    drive_path = target_dir
    while not drive_path.exists() and drive_path.parent != drive_path:
        drive_path = drive_path.parent
    total_space, used_space, free_space = shutil.disk_usage(drive_path)
    free_gb = free_space / (1024**3)
    print(f" Диск назначения: {drive_path} (Свободно: {free_gb:.1f} GB)")

    items = get_model_items(quant, base_dir, with_dflash=args.with_dflash)
    if args.no_vision:
        items = [x for x in items if x["category"] != "vision_tower"]

    # Проверка целостности (если запрошен --verify-checksums)
    if args.verify_checksums:
        print("\nРежим проверки существующих файлов (SHA256):")
        all_ok = True
        for it in items:
            p = it["dest"]
            if not p.exists():
                print(f"  [MISSING] {it['name']}: файл отсутствует")
                all_ok = False
                continue
            size = p.stat().st_size
            print(f"  [CHECKING] {it['name']} ({format_bytes(size)}) ...", end="", flush=True)
            calc_hash = sha256_file(p)
            expected = it["sha256"]
            valid = (calc_hash == expected) if isinstance(expected, str) else (calc_hash in [x.lower() for x in expected])
            if valid:
                print(" OK")
            else:
                print(f" MISMATCH! (Хэш: {calc_hash})")
                all_ok = False
        if all_ok:
            print("\n[OK] Все проверенные файлы соответствуют оригинальным контрольным суммам!")
        else:
            print("\n[ВНИМАНИЕ] Некоторые файлы отсутствуют или повреждены.")
        return 0 if all_ok else 1

    # Режим Dry Run
    if args.dry_run:
        print("\n[DRY RUN] Проверка доступности удаленных URL и структуры папок:")
        all_online = True
        for it in items:
            url = it["url"]
            print(f"  Проверка: {it['name']} ... ", end="", flush=True)
            status, size = check_url_head(url)
            if status in (200, 302, 307):
                print(f"ONLINE (HTTP {status}, {format_bytes(size)})")
            else:
                print(f"ОШИБКА ДОСТУПА (HTTP {status})")
                all_online = False
                
        print("\nРезультат проверки готовности к загрузке:")
        print(f"  * Структура каталогов: {target_dir}")
        print(f"  * Требуется места:      ~{m_info['download_gb'] + 1.5:.1f} GB")
        print(f"  * Доступно на диске:    {free_gb:.1f} GB")
        if free_gb < (m_info['download_gb'] + 3):
            print("  * [ПРЕДУПРЕЖДЕНИЕ] Недостаточно свободного места на выбранном диске!")
        else:
            print("  * [OK] Свободного места достаточно для полной загрузки модели и сборки pack!")

        if all_online:
            print("  * [OK] Все URL на Hugging Face подтверждены и доступны для докачки.")
            print("\nСкрипт полностью исправен и готов к выполнению скачивания по вашей команде.")
        else:
            print("  * [ОШИБКА] Один или несколько URL недоступны.")
        return 0

    # Реальная загрузка
    print("\nПодготовка к загрузке файлов...")
    target_dir.mkdir(parents=True, exist_ok=True)
    vision_dir = target_dir / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)

    curl_exe = shutil.which("curl")
    if not curl_exe:
        print("[ОШИБКА] Утилита curl не найдена в системе. Установите curl для продолжения.")
        return 1

    for idx, it in enumerate(items, 1):
        dst = it["dest"]
        url = it["url"]
        name = it["name"]
        
        print(f"\n[{idx}/{len(items)}] Загрузка {name}...")
        print(f"  Куда: {dst}")
        print(f"  URL:  {url}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Проверка, скачан ли файл уже полностью
        if dst.exists() and dst.stat().st_size > 0:
            existing_size = dst.stat().st_size
            print(f"  Файл уже существует на диске ({format_bytes(existing_size)}). Проверка докачки...")

        # Вызов curl в точности с ключами, которые использует Project Maya:
        # -L: следовать редиректам (CDN)
        # --fail: аварийное завершение при ошибках сервера (4xx/5xx)
        # --retry 5: повторные попытки при обрыве связи
        # -C -: автоматическое возобновление скачивания с прерванного места
        cmd = [curl_exe, "-L", "--fail", "--retry", "5", "-C", "-", "-o", str(dst), url]
        
        res = os.system(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        if res != 0:
            print(f"\n[ОШИБКА] Загрузка {name} прервана с кодом {res}.")
            print("Вы можете запустить скрипт снова в любое время — он продолжит скачивание с места остановки.")
            return 1

        # Проверка SHA-256 после завершения загрузки файла
        expected_sha = it["sha256"]
        if expected_sha:
            print(f"  Проверка SHA-256 для {name} ...", end="", flush=True)
            calc_hash = sha256_file(dst)
            valid = (calc_hash == expected_sha) if isinstance(expected_sha, str) else (calc_hash in [x.lower() for x in expected_sha])
            if valid:
                print(" OK")
            else:
                print(f"\n[ВНИМАНИЕ] Несовпадение контрольной суммы! Хэш: {calc_hash}")
                return 1

    print("\n" + "=" * 70)
    print(" [УСПЕХ] Все файлы модели успешно загружены и проверены!")
    print(f" Файлы размещены в: {target_dir}")
    print(" Теперь Project Maya автоматически найдет модель без повторной загрузки.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
