#!/usr/bin/env python3
"""
=================================================
  QR Code Generator (CLI + Tkinter GUI) + QR Studio
  Membuat QR code dari URL atau teks
=================================================

Instalasi dependensi (sekali saja):
    pip install qrcode pillow

Cara pakai:

  1. MODE CLI (sederhana - cukup ketik teks/URL)
  ----------------
  python qr_generator.py "https://example.com" -o hasil.png
  python qr_generator.py "Hello QR World!" --style Ocean --scan-text "Scan Me"

  Opsi:
    -o / --output      : nama file output (default: qrcode_<timestamp>.png)
    -e / --ecc         : level error correction (L / M / Q / H), default: H
    --box-size         : ukuran modul (pixel) tiap titik, default: 10
    --border           : lebar border quiet zone, default: 4
    --fg / --bg        : warna kode QR dan warna latar, format hex (default: #000000 / #FFFFFF)
    --style            : preset gaya estetik QR (Classic, Midnight, Ocean, Sunset, Lush, Royal, Candy)
    --scan-text        : teks tambahan di bawah QR, misal: "Scan Me"

  2. MODE GUI (Tkinter) + QR STUDIO
  ----------------
  python qr_generator.py --gui

  Fitur GUI:
    - Input teks / URL
    - Studio: pilih preset gaya QR estetik + edit teks (mis. "Scan Me")
    - Edit warna kode QR & warna latar
    - Atur ukuran modul
    - Pilih level error correction
    - Preview langsung + simpan sebagai PNG
"""

import argparse
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import qrcode
import qrcode.constants
from PIL import Image, ImageDraw, ImageFont, ImageTk

DEFAULT_ECC = qrcode.constants.ERROR_CORRECT_H
DEFAULT_BOX_SIZE = 10
DEFAULT_BORDER = 4
DEFAULT_FG = "#000000"
DEFAULT_BG = "#FFFFFF"
PREVIEW_MAX_SIZE = 360  # ukuran maksimum preview di GUI (piksel)

# ==========================================================
# QR STUDIO - Preset gaya estetik QR
# ==========================================================
STYLES = [
    {"name": "Classic",  "fg": "#000000", "bg": "#FFFFFF", "gradient": False, "radius": 0},
    {"name": "Midnight", "fg": "#22D3EE", "bg": "#0F172A", "gradient": True,  "radius": 0},
    {"name": "Ocean",    "fg": "#2563EB", "bg": "#EFF6FF", "gradient": True,  "radius": 2},
    {"name": "Sunset",   "fg": "#F97316", "bg": "#FFF7ED", "gradient": True,  "radius": 2},
    {"name": "Lush",     "fg": "#16A34A", "bg": "#F0FDF4", "gradient": True,  "radius": 2},
    {"name": "Royal",    "fg": "#7C3AED", "bg": "#FAF5FF", "gradient": True,  "radius": 3},
    {"name": "Candy",    "fg": "#EC4899", "bg": "#FDF2F8", "gradient": True,  "radius": 4},
]
STYLES_MAP = {s["name"]: s for s in STYLES}


# ==========================================================
# FUNGSI GENERASI
# ==========================================================
def _hex_to_rgb(h):
    h = (h or "#000000").lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


def _lighten(rgb, factor=0.7):
    """Mencerahkan warna menuju putih."""
    return tuple(int(round(v + (255 - v) * factor)) for v in rgb)


def render_qr(data, ecc=DEFAULT_ECC, box_size=DEFAULT_BOX_SIZE, border=DEFAULT_BORDER, style=None, text=None):
    """Membuat gambar QR Code (dengan gaya/studio) dari teks/URL."""
    style = style or STYLES_MAP["Classic"]
    qr = qrcode.QRCode(
        version=None,           # otomatis pilih versi QR yang tepat
        error_correction=ecc,   # level error correction
        box_size=box_size,       # pixel per modul
        border=border,           # quiet zone (border putih)
    )
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.modules
    m = len(matrix)

    fg = _hex_to_rgb(style.get("fg") or DEFAULT_FG)
    bg = _hex_to_rgb(style.get("bg") or DEFAULT_BG)
    gradient = bool(style.get("gradient"))
    radius = int(style.get("radius") or 0)

    size = (m + 2 * border) * box_size
    text_h = 0
    font = None
    if text and text.strip():
        try:
            font = ImageFont.load_default(size=max(12, int(box_size * 0.8)))
        except Exception:
            font = ImageFont.load_default()
        bb = font.getbbox(text.strip())
        text_h = max(10, int(bb[3] - bb[1]))
    canvas_h = size + (int(box_size * 0.8) * 2 + text_h if text and text.strip() else 0)

    img = Image.new("RGB", (size, canvas_h), bg)
    draw = ImageDraw.Draw(img)

    for r in range(m):
        for c in range(m):
            if matrix[r][c]:
                x = (c + border) * box_size
                y = (r + border) * box_size
                col = fg
                if gradient and m > 1:
                    t = (c + r) / (2 * (m - 1))          # gradien diagonal
                    col = _mix(fg, _lighten(fg, 0.7), t)
                if radius > 0:
                    rr = min(radius, box_size // 2)
                    draw.rounded_rectangle([x, y, x + box_size, y + box_size], radius=rr, fill=col)
                else:
                    draw.rectangle([x, y, x + box_size, y + box_size], fill=col)

    if text and text.strip() and font is not None:
        tw = int(draw.textlength(text.strip(), font=font))
        draw.text(((size - tw) // 2, size + int(box_size * 0.8)), text.strip(), font=font, fill=fg)

    return img


def scale_for_preview(img, max_size=PREVIEW_MAX_SIZE):
    """Mengubah ukuran gambar supaya muat di preview GUI."""
    w, h = img.size
    if w <= max_size and h <= max_size:
        return img
    ratio = max_size / max(w, h)
    return img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)


# ==========================================================
# MODE CLI
# ==========================================================
def run_cli(args):
    data = (args.text or "").strip()
    if not data:
        print("Error: teks/URL tidak boleh kosong. Contoh: python qr_generator.py 'https://example.com'")
        return 1

    style = dict(STYLES_MAP.get(args.style, STYLES_MAP["Classic"]))
    style["fg"] = args.fg or style["fg"]
    style["bg"] = args.bg or style["bg"]
    print(f"Membuat QR code untuk: {data}")

    img = render_qr(
        data,
        ecc=getattr(qrcode.constants, f"ERROR_CORRECT_{args.ecc}"),
        box_size=args.box_size,
        border=args.border,
        style=style,
        text=args.scan_text,
    )

    output = args.output or f"qrcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    img.save(output, format="PNG")

    print(f"QR code berhasil dibuat!")
    print(f"  Isi       : {data}")
    print(f"  Gaya      : {style['name']}")
    print(f"  Ekstensi : {args.ecc}")
    print(f"  Ukuran   : {img.size[0]} x {img.size[1]} px")
    print(f"  Disimpan : {os.path.abspath(output)}")

    return 0


# ==========================================================
# MODE GUI (Tkinter) + QR STUDIO
# ==========================================================
class QRGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QR Code Generator")
        self.geometry("440x760")
        self.resizable(False, False)

        self.current_img = None      # PIL Image aktif
        self.current_photo = None    # ImageTk.PhotoImage aktif (keep ref)

        self.style = dict(STYLES_MAP["Classic"])
        self.style_name = "Classic"

        self.fg_var = tk.StringVar(value=self.style["fg"])
        self.bg_var = tk.StringVar(value=self.style["bg"])
        self.box_size_var = tk.IntVar(value=DEFAULT_BOX_SIZE)
        self.ecc_var = tk.StringVar(value="H")
        self.scan_text_var = tk.StringVar(value="Scan Me")

        self._build_widgets()
        self._show_empty_preview()

    # ---------- layout ----------
    def _build_widgets(self):
        tk.Label(self, text="QR Code Generator", font=("Segoe UI", 20, "bold")).pack(pady=10)

        tk.Label(self, text="Masukkan URL atau teks:", font=("Segoe UI", 10)).pack(anchor="w", padx=15, pady=6)

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.entry_var, font=("Segoe UI", 11), width=42)
        self.entry.pack(fill="x", padx=15, pady=4)
        self.entry.focus()

        frame_ecc = tk.Frame(self)
        frame_ecc.pack(fill="x", padx=15, pady=2)
        tk.Label(frame_ecc, text="Ekstensi:", font=("Segoe UI", 10)).pack(side="left")
        self.ecc_combo = ttk.Combobox(frame_ecc, textvariable=self.ecc_var, values=["L", "M", "Q", "H"], state="readonly", width=8)
        self.ecc_combo.pack(side="right")

        # ---------- QR STUDIO ----------
        studio = tk.LabelFrame(self, text="QR Studio - Gaya Estetik", padx=10, pady=8)
        studio.pack(fill="x", padx=15, pady=8)

        tk.Label(studio, text="Preset Gaya:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        self.style_var = tk.StringVar(value="Classic")
        self.style_combo = ttk.Combobox(studio, textvariable=self.style_var, values=[s["name"] for s in STYLES], state="readonly", width=12)
        self.style_combo.grid(row=0, column=1, padx=8, pady=4, sticky="w")
        self.style_combo.bind("<<ComboboxSelected>>", self.on_style_change)

        tk.Label(studio, text="Teks di bawah QR (cth: Scan Me):", font=("Segoe UI", 10)).grid(row=1, column=0, padx=0, pady=4, sticky="w")
        self.scan_entry = ttk.Entry(studio, textvariable=self.scan_text_var, font=("Segoe UI", 10), width=20)
        self.scan_entry.grid(row=1, column=1, padx=8, pady=4, sticky="w")

        # ---------- Edit Warna ----------
        frame_colors = tk.LabelFrame(self, text="Edit Warna", padx=10, pady=8)
        frame_colors.pack(fill="x", padx=15, pady=4)

        self.fg_btn = tk.Button(frame_colors, text="  Warna Kode QR  ", bg=self.fg_var.get(), activebackground=self.fg_var.get(), relief="solid", width=14, command=self.on_pick_fg)
        self.fg_btn.grid(row=0, column=0, padx=5)

        self.bg_btn = tk.Button(frame_colors, text="  Warna Latar  ", bg=self.bg_var.get(), activebackground=self.bg_var.get(), relief="solid", width=14, command=self.on_pick_bg)
        self.bg_btn.grid(row=0, column=1, padx=5)

        # ---------- Edit Ukuran ----------
        tk.Label(self, text="Ukuran Modul (px):", font=("Segoe UI", 10)).pack(anchor="w", padx=15, pady=(10, 0))
        self.scale = ttk.Scale(self, from_=4, to=20, orient="horizontal", variable=self.box_size_var, value=DEFAULT_BOX_SIZE)
        self.scale.pack(fill="x", padx=15, pady=4)

        btn_generate = ttk.Button(self, text="Buat QR Code", command=self.on_generate)
        btn_generate.pack(pady=10)

        self.preview_label = tk.Label(self, bg="white", borderwidth=1, relief="solid")
        self.preview_label.pack(padx=15, pady=8, ipadx=20, ipady=20)

        btn_save = ttk.Button(self, text="Simpan Sebagai PNG...", command=self.on_save)
        btn_save.pack(pady=12)

        self.status_var = tk.StringVar(value="Siap. Masukkan teks/URL lalu klik 'Buat QR Code'.")
        status = tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 9), fg="gray")
        status.pack(pady=4)

    # ---------- tampilkan preview kosong ----------
    def _show_empty_preview(self):
        self.preview_label.configure(image=None)
        self.status_var.set("Siap. Masukkan teks/URL lalu klik 'Buat QR Code'.")

    # ---------- aksi gaya studio ----------
    def on_style_change(self, event=None):
        name = self.style_var.get()
        if name in STYLES_MAP:
            self.style = dict(STYLES_MAP[name])
            self.style_name = name
            self.fg_var.set(self.style["fg"])
            self.bg_var.set(self.style["bg"])
            self.fg_btn.configure(bg=self.style["fg"])
            self.bg_btn.configure(bg=self.style["bg"])

    # ---------- aksi pemilihan warna ----------
    def on_pick_fg(self):
        color, hexv = tk.colorchooser.askcolor(initialcolor=self.fg_var.get(), parent=self, title="Pilih Warna Kode QR")
        if hexv:
            self.style["fg"] = hexv
            self.style_name = "Custom"
            self.fg_var.set(hexv)
            self.fg_btn.configure(bg=hexv)

    def on_pick_bg(self):
        color, hexv = tk.colorchooser.askcolor(initialcolor=self.bg_var.get(), parent=self, title="Pilih Warna Latar")
        if hexv:
            self.style["bg"] = hexv
            self.style_name = "Custom"
            self.bg_var.set(hexv)
            self.bg_btn.configure(bg=hexv)

    # ---------- aksi generate ----------
    def on_generate(self):
        data = self.entry_var.get().strip()
        if not data:
            messagebox.showwarning("Peringatan", "Masukkan dulu URL atau teksnya.")
            return

        try:
            ecc = getattr(qrcode.constants, f"ERROR_CORRECT_{self.ecc_var.get()}")
            img = render_qr(
                data,
                ecc=ecc,
                box_size=self.box_size_var.get(),
                border=DEFAULT_BORDER,
                style=self.style,
                text=self.scan_text_var.get().strip() or None,
            )
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuat QR code:\n{e}")
            return

        self.current_img = img
        self.current_photo = ImageTk.PhotoImage(scale_for_preview(img))
        self.preview_label.configure(image=self.current_photo)
        self.status_var.set(f"Berhasil! QR code siap. ({img.size[0]}x{img.size[1]} px)")

    # ---------- aksi simpan ----------
    def on_save(self):
        if self.current_img is None:
            messagebox.showwarning("Info", "Buat dulu QR code-nya (tombol 'Buat QR Code').")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("Semua File", "*.*")],
            title="Simpan QR Code",
        )
        if not path:
            return
        try:
            self.current_img.save(path, format="PNG")
            messagebox.showinfo("Berhasil", f"QR code disimpan ke:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan:\n{e}")


def launch_gui():
    app = QRGUI()
    app.mainloop()
    return 0


# ==========================================================
# ENTRY POINT
# ==========================================================
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="qr_generator",
        description="Membuat QR code dari URL atau teks.",
        epilog="Contoh: python qr_generator.py 'https://example.com' -o qr.png",
    )
    parser.add_argument("text", nargs="?", help="Teks atau URL yang ingin dibuatkan QR-nya.")
    parser.add_argument("-o", "--output", help="Nama file output (default: qrcode_<timestamp>.png).")
    parser.add_argument("-e", "--ecc", default="H", choices=["L", "M", "Q", "H"], help="Level error correction (default: H).")
    parser.add_argument("--box-size", type=int, default=10, help="Ukuran modul per titik (pixel, default: 10).")
    parser.add_argument("--border", type=int, default=4, help="Lebar border quiet zone (default: 4).")
    parser.add_argument("--fg", "--foreground", default=None, help="Warna kode QR, format hex (default: dari preset style).")
    parser.add_argument("--bg", "--background", default=None, help="Warna latar, format hex (default: dari preset style).")
    parser.add_argument("--style", default="Classic", choices=[s["name"] for s in STYLES], help="Preset gaya estetik QR.")
    parser.add_argument("--scan-text", default=None, help="Teks tambahan di bawah QR, misal: 'Scan Me'.")
    parser.add_argument("--gui", action="store_true", help="Buka mode GUI (Tkinter).")

    args = parser.parse_args(argv)

    # Tanpa argumen teks -> buka GUI
    if args.gui or not args.text:
        return launch_gui()

    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
