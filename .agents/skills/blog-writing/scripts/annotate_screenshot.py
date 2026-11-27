#!/usr/bin/env python3
"""
남주의 커밋로그(namju.kim) 웹 캡처 후처리 스크립트 (부분 파싱·타이트 크롭·강조·마스킹).

Antigravity 내장 사이드바 `browser` 서브에이전트로 캡처한 원본 스크린샷에서
핵심 UI 영역만 정밀하게 잘라내고(부분 파싱), 클릭 지점 강조 박스·번호 배지·민감정보
블러/마스킹을 적용해 블로그 본문 최적 크기(<= 1400px, <= 1MB)로 저장합니다.

필요 패키지:
  pip install pillow

사용 예시:
  # 1) 퍼센트 기준 부분 크롭 + 강조 박스 + 번호 배지 + 민감정보 블러
  python3 .agents/skills/blog-writing/scripts/annotate_screenshot.py \
    --in /path/to/raw-capture.png \
    --out assets/images/2026-11-27/sonarcloud-toggle.webp \
    --crop-pct 15,10,70,65 \
    --box 420,180,260,48 \
    --badge 405,180,1 \
    --blur 60,40,240,28

  # 2) 픽셀 크롭 + 자동 여백 제거 + PNG 저장
  python3 .agents/skills/blog-writing/scripts/annotate_screenshot.py \
    --in /path/to/raw-capture.png \
    --out assets/images/2026-11-27/devtools-waterfall.png \
    --crop 0,80,1280,540 \
    --auto-trim \
    --max-width 1400
"""

import argparse
import os
import sys

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print(
        "[ERROR] Pillow 패키지가 필요합니다. 아래 명령으로 설치해 주세요:\n"
        "  pip install pillow",
        file=sys.stderr,
    )
    sys.exit(1)

HIGHLIGHT_COLOR = (239, 68, 68)  # Tailwind Red-500
BADGE_BG = (239, 68, 68)
BADGE_FG = (255, 255, 255)
MASK_COLOR = (17, 24, 39)


def parse_rect(spec, is_float=False):
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) != 4:
        raise ValueError(f"좌표는 x,y,w,h 4개 값이어야 합니다: {spec}")
    conv = float if is_float else int
    x, y, w, h = (conv(p) for p in parts)
    if w <= 0 or h <= 0:
        raise ValueError(f"너비와 높이는 양수여야 합니다: {spec}")
    return x, y, w, h


def parse_badge(spec):
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) != 3:
        raise ValueError(f"배지는 x,y,라벨 3개 값이어야 합니다: {spec}")
    return int(parts[0]), int(parts[1]), parts[2]


def find_font(size):
    win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    candidates = [
        os.path.join(win_fonts, "malgunbd.ttf"),
        os.path.join(win_fonts, "arialbd.ttf"),
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def auto_trim(img, pad=12, tolerance=10):
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    diff = ImageChops.difference(rgb, bg)
    diff = diff.point(lambda p: 255 if p > tolerance else 0)
    bbox = diff.getbbox()
    if not bbox:
        return img
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(img.width, bbox[2] + pad)
    bottom = min(img.height, bbox[3] + pad)
    return img.crop((left, top, right, bottom))


def clamp_box(img, x, y, w, h):
    x0 = max(0, min(img.width, x))
    y0 = max(0, min(img.height, y))
    x1 = max(x0, min(img.width, x + w))
    y1 = max(y0, min(img.height, y + h))
    return x0, y0, x1, y1


def main():
    parser = argparse.ArgumentParser(
        description="웹 캡처 부분 크롭·강조·민감정보 마스킹 및 블로그 최적화 저장"
    )
    parser.add_argument("--in", dest="in_path", required=True, help="원본 캡처 이미지 경로")
    parser.add_argument("--out", dest="out_path", required=True, help="저장할 이미지 경로 (.png / .webp)")
    parser.add_argument("--crop", help="픽셀 기준 부분 크롭 (x,y,w,h)")
    parser.add_argument("--crop-pct", help="퍼센트 기준 부분 크롭 (x,y,w,h, 0~100)")
    parser.add_argument("--auto-trim", action="store_true", help="외곽 단색 여백 자동 제거")
    parser.add_argument("--trim-pad", type=int, default=12, help="자동 트림 시 보존할 여백(px)")
    parser.add_argument("--blur", action="append", default=[], help="가우시안 블러 영역 (x,y,w,h, 반복 가능)")
    parser.add_argument("--mask", action="append", default=[], help="솔리드 블랙박스 마스킹 영역 (x,y,w,h, 반복 가능)")
    parser.add_argument("--box", action="append", default=[], help="강조 사각형 영역 (x,y,w,h, 반복 가능)")
    parser.add_argument("--badge", action="append", default=[], help="번호 원형 배지 (x,y,라벨, 반복 가능)")
    parser.add_argument("--max-width", type=int, default=1400, help="최대 가로 폭(px, 기본 1400)")
    parser.add_argument("--quality", type=int, default=85, help="WebP/JPEG 품질 (기본 85)")
    args = parser.parse_args()

    img = Image.open(args.in_path).convert("RGBA")

    # 1. 부분 크롭 (픽셀 또는 퍼센트)
    if args.crop and args.crop_pct:
        parser.error("--crop과 --crop-pct는 동시에 사용할 수 없습니다.")
    if args.crop:
        x, y, w, h = parse_rect(args.crop)
        img = img.crop(clamp_box(img, x, y, w, h))
    elif args.crop_pct:
        px, py, pw, ph = parse_rect(args.crop_pct, is_float=True)
        x = int(img.width * px / 100.0)
        y = int(img.height * py / 100.0)
        w = int(img.width * pw / 100.0)
        h = int(img.height * ph / 100.0)
        img = img.crop(clamp_box(img, x, y, w, h))

    if args.auto_trim:
        img = auto_trim(img, pad=args.trim_pad)

    # 2. 민감 정보 블러 / 솔리드 마스킹 (크롭 후 좌표 기준)
    for spec in args.blur:
        x0, y0, x1, y1 = clamp_box(img, *parse_rect(spec))
        if x1 > x0 and y1 > y0:
            region = img.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(radius=14))
            img.paste(region, (x0, y0))

    draw = ImageDraw.Draw(img)
    for spec in args.mask:
        x0, y0, x1, y1 = clamp_box(img, *parse_rect(spec))
        if x1 > x0 and y1 > y0:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=MASK_COLOR)

    # 3. 클릭 지점 강조 사각형 & 번호 배지
    for spec in args.box:
        x0, y0, x1, y1 = clamp_box(img, *parse_rect(spec))
        if x1 > x0 and y1 > y0:
            draw.rounded_rectangle(
                [x0, y0, x1, y1],
                radius=6,
                outline=HIGHLIGHT_COLOR,
                width=4,
            )

    badge_font = find_font(18)
    for spec in args.badge:
        cx, cy, label = parse_badge(spec)
        r = 16
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BADGE_BG, outline=(255, 255, 255), width=2)
        tb = draw.textbbox((0, 0), label, font=badge_font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        draw.text((cx - tw / 2, cy - th / 2 - 2), label, font=badge_font, fill=BADGE_FG)

    # 4. 최대 가로 폭 리사이즈 (업스케일 금지)
    if args.max_width and img.width > args.max_width:
        ratio = args.max_width / float(img.width)
        new_h = max(1, int(img.height * ratio))
        img = img.resize((args.max_width, new_h), Image.Resampling.LANCZOS)

    # 5. 최적화 저장
    out_dir = os.path.dirname(os.path.abspath(args.out_path))
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(args.out_path)[1].lower()
    if ext == ".webp":
        img.convert("RGB").save(args.out_path, format="WEBP", quality=args.quality, method=6)
    elif ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(args.out_path, format="JPEG", quality=args.quality, optimize=True)
    else:
        img.save(args.out_path, format="PNG", optimize=True)

    size_kb = os.path.getsize(args.out_path) / 1024
    print(f"Saved screenshot: {args.out_path} ({img.width}x{img.height}, {size_kb:.1f} KB)")
    if size_kb > 1024:
        print("[WARNING] 파일 크기가 1MB를 초과했습니다. .webp 변환이나 --max-width 축소를 권장합니다.", file=sys.stderr)


if __name__ == "__main__":
    main()
