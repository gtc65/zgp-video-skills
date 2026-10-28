"""照片總覽表：把一個資料夾的照片排成編號縮圖表（每張 6×4 格），方便 Claude 和使用者一起挑照片、分段。
用法：python contact_sheet.py <照片資料夾> <輸出資料夾> [--cols 6] [--rows 4] [--width 2400]
輸出：sheet01.jpg、sheet02.jpg…，以及 photos.json（檔名、拍攝時間、寬高、直/橫）。
會自動依 EXIF 轉正，依拍攝時間排序（沒有 EXIF 時用檔名）。HEIC 需要 python -m pip install pillow-heif。"""
import argparse
import json
from pathlib import Path

from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
DT = next(k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal")


def font(size):
    for f in ["C:/Windows/Fonts/msjh.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/System/Library/Fonts/PingFang.ttc"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--cols", type=int, default=6); ap.add_argument("--rows", type=int, default=4); ap.add_argument("--width", type=int, default=2400)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(x for x in src.rglob("*") if x.suffix.lower() in EXT):
        try:
            im = Image.open(p)
            when = (im.getexif().get_ifd(0x8769).get(DT) or im.getexif().get(306) or "")
            im = ImageOps.exif_transpose(im)
            items.append({"file": str(p.relative_to(src)), "time": str(when), "w": im.width, "h": im.height,
                          "orient": "直" if im.height > im.width else "橫"})
        except Exception as e:
            print("略過", p.name, e)
    items.sort(key=lambda x: (x["time"] or "9", x["file"]))
    cw = a.width // a.cols; ch = round(cw * 0.75) + 34; per = a.cols * a.rows; f = font(22)
    for s in range(0, len(items), per):
        sheet = Image.new("RGB", (a.width, ch * a.rows), (30, 30, 30)); d = ImageDraw.Draw(sheet)
        for k, it in enumerate(items[s:s + per]):
            im = ImageOps.exif_transpose(Image.open(src / it["file"])).convert("RGB"); im.thumbnail((cw - 8, ch - 42))
            x, y = (k % a.cols) * cw, (k // a.cols) * ch
            sheet.paste(im, (x + (cw - im.width) // 2, y + 4))
            d.text((x + 6, y + ch - 32), f"{s + k + 1:03d} {Path(it['file']).name[:22]}", font=f, fill=(255, 230, 120))
            it["no"] = s + k + 1
        sheet.save(out / f"sheet{s // per + 1:02d}.jpg", quality=85)
    (out / "photos.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} 張照片 → {(len(items) + per - 1) // per} 張總覽表：{out}")


if __name__ == "__main__":
    main()
