#!/usr/bin/env python3
"""
남주의 커밋로그(namju.kim) 터미널 실행 결과 캡처 PNG 생성기.

특징:
- Tokyo Night 다크 테마 + macOS 윈도우 스타일(신호등 버튼, 타이틀바, 둥근 모서리)
- 실제 텍스트 줄 수에 맞춘 자동 세로 높이(타이트 크롭, 하단 불필요 여백 제거)
- D2Coding 우선(한글·영문 2:1 고정폭 완벽 정렬), 미설치 시 Menlo/DejaVu 자동 fallback
- 인라인 색상 태그 지원: [green]...[/], [cyan]...[/], [yellow]...[/], [red]...[/],
  [blue]...[/], [magenta]...[/], [muted]...[/], [bold]...[/]

사용 예시:
  # 1) stdin으로 전달
  cat << 'EOF' | python3 .agents/skills/blog-writing/scripts/render_terminal.py \
      --title "zsh — ./gradlew test" \
      --out assets/images/2026-11-24/gradle-test-pass.png
  [green]kimnamju@mbp[/]:[blue]~/projects/demo[/]$ ./gradlew test
  [muted]> Task :compileJava UP-TO-DATE[/]
  [green]✓[/] OrderServiceTest > 정상 주문 생성 [muted](42ms)[/]
  [green]BUILD SUCCESSFUL[/] in 1s
  EOF

  # 2) 텍스트 파일 입력
  python3 .agents/skills/blog-writing/scripts/render_terminal.py \
      --title "zsh — docker compose ps" \
      --input /tmp/output.txt \
      --out assets/images/2026-11-24/docker-ps.png
"""

import argparse
import glob
import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

# Tokyo Night color palette
BG_OUTER = (15, 17, 26)
BG_WINDOW = (26, 27, 38)
BG_TITLEBAR = (22, 22, 30)
BORDER_COLOR = (52, 56, 78)
TITLE_COLOR = (134, 140, 170)

COLORS = {
    "default": (192, 202, 245),
    "white": (228, 234, 255),
    "green": (158, 206, 106),
    "cyan": (125, 207, 255),
    "blue": (122, 162, 247),
    "yellow": (224, 175, 104),
    "orange": (255, 158, 100),
    "red": (247, 118, 142),
    "magenta": (187, 154, 247),
    "muted": (115, 122, 162),
    "bold": (236, 240, 255),
}

TAG_PATTERN = re.compile(
    r"\[(" + "|".join(COLORS.keys()) + r")\](.*?)\[/\]"
)


def find_font(size):
    candidates = (
        glob.glob(os.path.expanduser("~/Library/Fonts/D2Coding*.ttc"))
        + glob.glob(os.path.expanduser("~/Library/Fonts/D2Coding*.ttf"))
        + [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def parse_segments(line):
    """Parse [color]text[/] tags into list of (text, rgb_color)."""
    segments = []
    pos = 0
    for m in TAG_PATTERN.finditer(line):
        if m.start() > pos:
            segments.append((line[pos : m.start()], COLORS["default"]))
        color_name = m.group(1)
        segments.append((m.group(2), COLORS[color_name]))
        pos = m.end()
    if pos < len(line):
        segments.append((line[pos:], COLORS["default"]))
    return segments if segments else [("", COLORS["default"])]


def render_terminal(lines, title, out_path, width=1200, font_size=20):
    font = find_font(font_size)
    title_font = find_font(max(14, font_size - 4))

    outer_pad = 24
    titlebar_h = 46
    pad_x = 28
    pad_top = 24
    pad_bottom = 28
    line_height = int(font_size * 1.55)

    # Strip trailing blank lines so output stays tightly cropped
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        lines = [""]

    content_h = pad_top + len(lines) * line_height + pad_bottom
    win_w = width - outer_pad * 2
    win_h = titlebar_h + content_h
    total_h = win_h + outer_pad * 2

    img = Image.new("RGB", (width, total_h), BG_OUTER)
    draw = ImageDraw.Draw(img)

    # Rounded terminal window
    x0, y0 = outer_pad, outer_pad
    x1, y1 = outer_pad + win_w, outer_pad + win_h
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=14,
        fill=BG_WINDOW,
        outline=BORDER_COLOR,
        width=2,
    )

    # Titlebar background
    draw.rounded_rectangle(
        [x0 + 1, y0 + 1, x1 - 1, y0 + titlebar_h],
        radius=13,
        fill=BG_TITLEBAR,
    )
    draw.rectangle(
        [x0 + 1, y0 + titlebar_h - 14, x1 - 1, y0 + titlebar_h],
        fill=BG_TITLEBAR,
    )
    draw.line(
        [(x0 + 1, y0 + titlebar_h), (x1 - 1, y0 + titlebar_h)],
        fill=BORDER_COLOR,
        width=1,
    )

    # macOS traffic light dots
    dot_y = y0 + titlebar_h // 2
    dot_r = 7
    for idx, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = x0 + 24 + idx * 24
        draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=color)

    # Centered window title
    if title:
        tb = draw.textbbox((0, 0), title, font=title_font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        draw.text(
            (x0 + (win_w - tw) // 2, y0 + (titlebar_h - th) // 2 - 2),
            title,
            font=title_font,
            fill=TITLE_COLOR,
        )

    # Draw terminal lines
    cur_y = y0 + titlebar_h + pad_top
    for raw_line in lines:
        cur_x = x0 + pad_x
        for text, color in parse_segments(raw_line):
            if not text:
                continue
            draw.text((cur_x, cur_y), text, font=font, fill=color)
            bbox = draw.textbbox((0, 0), text, font=font)
            cur_x += bbox[2] - bbox[0]
        cur_y += line_height

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    print(f"Saved terminal screenshot: {out_path} ({width}x{total_h})")


def main():
    parser = argparse.ArgumentParser(description="Render macOS dark terminal screenshot PNG.")
    parser.add_argument("--title", default="zsh — namju.kim", help="Window title text")
    parser.add_argument("--input", "-i", help="Input text file (defaults to stdin)")
    parser.add_argument("--out", "-o", required=True, help="Output PNG path")
    parser.add_argument("--width", type=int, default=1200, help="Image width in px (default: 1200)")
    parser.add_argument("--font-size", type=int, default=20, help="Font size in px (default: 20)")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    render_terminal(lines, args.title, args.out, width=args.width, font_size=args.font_size)


if __name__ == "__main__":
    main()
