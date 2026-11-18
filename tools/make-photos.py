"""把原始照片生成四档图（orig / full 1920 / mid 1024 / thumb 512）+ manifest.json

用法：
    python tools/make-photos.py <原图目录> <输出目录>

规则：
- 先按 EXIF 方向摆正（竖拍不会躺倒），再等比缩放到「最长边」，不裁脸。
- 三档 WebP 质量跟随原模板：thumb q80 / mid q84 / full q88。
- manifest 里的 w / h 记原始像素（摆正后），代码用它判断是否超过显卡纹理上限。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

STEPS = [("thumb", 512, 80), ("mid", 1024, 84), ("full", 1920, 88)]
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])

    files = sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS)
    if not files:
        print("没有找到图片:", src)
        return 1

    for sub in ["orig"] + [s[0] for s in STEPS]:
        (out / sub).mkdir(parents=True, exist_ok=True)

    photos = []
    for i, f in enumerate(files, 1):
        pid = f"photo{i:02d}"
        im = ImageOps.exif_transpose(Image.open(f))
        w, h = im.size
        has_alpha = im.mode in ("RGBA", "LA", "P")
        base = im.convert("RGBA") if has_alpha else im.convert("RGB")

        # 原图：保留原文件（跟模板一致，按 O 键下载的就是它）
        orig_name = f"{pid}{f.suffix.lower()}"
        (out / "orig" / orig_name).write_bytes(f.read_bytes())

        entry = {
            "id": pid,
            "src": orig_name,
            "orig": f"orig/{orig_name}",
            "w": w,
            "h": h,
        }
        for name, long_edge, q in STEPS:
            scale = min(1.0, long_edge / max(w, h))
            tw, th = max(1, round(w * scale)), max(1, round(h * scale))
            resized = base.resize((tw, th), Image.LANCZOS)
            target = out / name / f"{pid}.webp"
            if has_alpha:
                resized.save(target, "WEBP", quality=q, method=6, exact=False)
            else:
                resized.save(target, "WEBP", quality=q, method=6)
            entry[name] = f"{name}/{pid}.webp"
            if name == "thumb":
                entry["thumbW"] = tw
                entry["thumbH"] = th
        photos.append(entry)
        print(f"{f.name} -> {pid}  {w}x{h}")

    manifest = {"photos": photos}
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"\n完成：{len(photos)} 张 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
