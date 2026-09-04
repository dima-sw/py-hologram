"""Hologram Studio - interfaccia grafica.

Avvio:  python main/app.py
"""

import os
import sys
import threading
import time

import customtkinter as ctk
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
from PIL import Image

import engine
import render3d

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_BASE = TkinterDnD.DnDWrapper
except Exception:  # il drag & drop e' un extra, non un requisito
    DND_FILES = None
    TkinterDnD = None
    DND_BASE = object

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, "holograms")

BG = ("#F4F5F9", "#0F1014")
CARD = ("#FFFFFF", "#191A21")
CARD_SOFT = ("#F0F1F6", "#20212A")
BORDER = ("#E1E3EC", "#282933")
TEXT = ("#15161C", "#F2F3F7")
MUTED = ("#6B6F80", "#898EA1")
ACCENT = "#7C5CFF"
ACCENT_HOVER = "#6A48F5"
SUCCESS = "#22C55E"
DANGER = "#EF4444"

QUALITY_PRESETS = {
    "Bassa": 200,
    "Media": 300,
    "Alta": 480,
    "Massima": 640,
}

BACKGROUND_PRESETS = {
    "Originale": "none",
    "Togli sfondo: movimento": "motion",
    "Togli sfondo: persona": "person",
    "Togli sfondo: oggetto": "object",
    "Solo fondo scuro": "black",
    "Green screen": "green",
}

# Un giro completo in otto secondi a 30 fotogrammi: abbastanza lento da
# leggere la forma, abbastanza breve da non annoiare in vetrina.
MODEL_SECONDS = 8.0
MODEL_FPS = 30.0
MODEL_TURNS = 1.0

# Oltre 0,5 il bagliore brucia i punti piu' chiari del soggetto.
GLOW_PRESETS = {
    "No": 0.0,
    "Lieve": 0.3,
    "Intenso": 0.5,
}


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024.0


def human_time(seconds):
    seconds = int(max(0, seconds))
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds}s"


class HologramApp(ctk.CTk, DND_BASE):
    def __init__(self):
        super().__init__()

        self.sources = []          # video in coda
        self.source_path = None    # quello mostrato in anteprima (il primo)
        self.source_info = None
        self.output_path = None    # destinazione del primo
        self.outputs = []
        self.worker = None
        self.cancel_flag = threading.Event()
        self.started_at = 0.0
        self.preview_image = None
        self.preview_token = 0

        self.title("Hologram Studio")
        self.geometry("880x700")
        self.minsize(820, 660)
        self.configure(fg_color=BG)

        self._build()
        self._enable_drag_and_drop()
        self._set_state("empty")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_stage()
        self._build_options()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Hologram Studio",
            font=ctk.CTkFont("Segoe UI", 27, "bold"), text_color=TEXT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text="Trasforma un video in un ologramma per display a piramide",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_menu = ctk.CTkOptionMenu(
            header, values=["Sistema", "Chiaro", "Scuro"], width=110, height=32,
            corner_radius=10, font=ctk.CTkFont("Segoe UI", 12),
            fg_color=CARD_SOFT, button_color=CARD_SOFT, button_hover_color=BORDER,
            text_color=TEXT, dropdown_font=ctk.CTkFont("Segoe UI", 12),
            command=self._change_theme,
        )
        self.theme_menu.set("Sistema")
        self.theme_menu.grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_stage(self):
        """Area centrale: zona di rilascio file oppure anteprima dal vivo."""
        self.stage = ctk.CTkFrame(
            self, corner_radius=18, fg_color=CARD,
            border_width=1, border_color=BORDER,
        )
        self.stage.grid(row=1, column=0, sticky="nsew", padx=28)
        self.stage.grid_columnconfigure(0, weight=1)
        self.stage.grid_rowconfigure(0, weight=1)

        # --- vista "scegli un file"
        self.drop_view = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.drop_view.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.drop_view.grid_columnconfigure(0, weight=1)
        self.drop_view.grid_rowconfigure(0, weight=1)
        self.drop_view.grid_rowconfigure(4, weight=1)

        self.drop_icon = ctk.CTkLabel(
            self.drop_view, text="🎬", font=ctk.CTkFont("Segoe UI Emoji", 52),
        )
        self.drop_icon.grid(row=1, column=0, pady=(0, 10))

        self.drop_title = ctk.CTkLabel(
            self.drop_view, text="Trascina qui un video",
            font=ctk.CTkFont("Segoe UI", 19, "bold"), text_color=TEXT,
        )
        self.drop_title.grid(row=2, column=0)

        self.drop_hint = ctk.CTkLabel(
            self.drop_view, text="oppure fai clic per sceglierlo dal computer",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        )
        self.drop_hint.grid(row=3, column=0, pady=(4, 0))

        for widget in (self.stage, self.drop_view, self.drop_icon,
                       self.drop_title, self.drop_hint):
            widget.bind("<Button-1>", lambda _e: self._pick_source())
            widget.configure(cursor="hand2")

        # --- vista "anteprima"
        self.preview_view = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.preview_view.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.preview_view.grid_columnconfigure(0, weight=1)
        self.preview_view.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_view, text="")
        self.preview_label.grid(row=0, column=0)

        self.preview_caption = ctk.CTkLabel(
            self.preview_view, text="", font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
        )
        self.preview_caption.grid(row=1, column=0, pady=(10, 0))
        self.preview_view.grid_remove()

    def _build_options(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=2, column=0, sticky="ew", padx=28, pady=(16, 0))
        panel.grid_columnconfigure(0, weight=1)

        # riga file selezionato
        self.file_row = ctk.CTkFrame(
            panel, corner_radius=14, fg_color=CARD, border_width=1, border_color=BORDER,
        )
        self.file_row.grid(row=0, column=0, sticky="ew")
        self.file_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.file_row, text="🎞", font=ctk.CTkFont("Segoe UI Emoji", 18),
        ).grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=12)

        self.file_name = ctk.CTkLabel(
            self.file_row, text="", anchor="w",
            font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=TEXT,
        )
        self.file_name.grid(row=0, column=1, sticky="ew", pady=(12, 0))

        self.file_meta = ctk.CTkLabel(
            self.file_row, text="", anchor="w",
            font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
        )
        self.file_meta.grid(row=1, column=1, sticky="ew", pady=(0, 12))

        self.btn_change = ctk.CTkButton(
            self.file_row, text="Cambia", width=84, height=32, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 12), fg_color=CARD_SOFT,
            hover_color=BORDER, text_color=TEXT, command=self._pick_source,
        )
        self.btn_change.grid(row=0, column=2, rowspan=2, padx=16)
        self.file_row.grid_remove()

        # riga impostazioni
        self.settings_row = ctk.CTkFrame(panel, fg_color="transparent")
        self.settings_row.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.settings_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.settings_row, text="Qualità",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        ).grid(row=0, column=0, padx=(2, 10))

        self.quality = ctk.CTkSegmentedButton(
            self.settings_row, values=list(QUALITY_PRESETS), height=34, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 12), selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=CARD,
            unselected_hover_color=CARD_SOFT, text_color=TEXT,
            command=lambda _v: self._refresh_estimate(),
        )
        self.quality.set("Media")
        self.quality.grid(row=0, column=1, sticky="w")

        self.loop = ctk.CTkSwitch(
            self.settings_row, text="Loop perfetto", font=ctk.CTkFont("Segoe UI", 13),
            text_color=TEXT, progress_color=ACCENT, button_color="#FFFFFF",
            command=self._look_changed,
        )
        self.loop.grid(row=0, column=2, padx=(18, 2))

        # riga aspetto
        self.look_row = ctk.CTkFrame(panel, fg_color="transparent")
        self.look_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.look_row.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            self.look_row, text="Sfondo",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        ).grid(row=0, column=0, padx=(2, 10))

        self.background = ctk.CTkOptionMenu(
            self.look_row, values=list(BACKGROUND_PRESETS), width=196, height=34,
            corner_radius=10, font=ctk.CTkFont("Segoe UI", 12),
            fg_color=CARD, button_color=CARD, button_hover_color=CARD_SOFT,
            text_color=TEXT, dropdown_font=ctk.CTkFont("Segoe UI", 12),
            command=lambda _v: self._look_changed(),
        )
        self.background.set("Originale")
        self.background.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            self.look_row, text="Bagliore",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        ).grid(row=0, column=2, padx=(18, 10))

        self.glow = ctk.CTkSegmentedButton(
            self.look_row, values=list(GLOW_PRESETS), height=34, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 12), selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=CARD,
            unselected_hover_color=CARD_SOFT, text_color=TEXT,
            command=lambda _v: self._look_changed(),
        )
        self.glow.set("No")
        self.glow.grid(row=0, column=3, sticky="w")

        self.autofit = ctk.CTkSwitch(
            self.look_row, text="Riempi la faccia", font=ctk.CTkFont("Segoe UI", 13),
            text_color=TEXT, progress_color=ACCENT, button_color="#FFFFFF",
            command=self._look_changed,
        )
        self.autofit.grid(row=0, column=4, padx=(18, 2), sticky="e")

        # avanzamento
        self.progress = ctk.CTkProgressBar(
            panel, height=8, corner_radius=6, progress_color=ACCENT, fg_color=CARD_SOFT,
        )
        self.progress.set(0)
        self.progress.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self.progress.grid_remove()

        self.status = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        )
        self.status.grid(row=4, column=0, pady=(8, 0))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=28, pady=(14, 24))
        footer.grid_columnconfigure(0, weight=1)

        self.btn_primary = ctk.CTkButton(
            footer, text="Crea ologramma", height=48, corner_radius=14,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            command=self._start,
        )
        self.btn_primary.grid(row=0, column=0, sticky="ew")

        self.btn_secondary = ctk.CTkButton(
            footer, text="Apri cartella", width=140, height=48, corner_radius=14,
            font=ctk.CTkFont("Segoe UI", 13), fg_color=CARD, hover_color=CARD_SOFT,
            text_color=TEXT, border_width=1, border_color=BORDER,
            command=self._open_output_folder,
        )
        self.btn_secondary.grid(row=0, column=1, padx=(12, 0))
        self.btn_secondary.grid_remove()

    # --------------------------------------------------------------- stati

    def _set_state(self, state):
        self.ui_state = state

        if state == "empty":
            self._show_stage("drop")
            self.file_row.grid_remove()
            self.progress.grid_remove()
            self.btn_secondary.grid_remove()
            self.status.configure(text=self._idle_hint(), text_color=MUTED)
            self.btn_primary.configure(
                text="Scegli un video", state="normal",
                fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._pick_source,
            )

        elif state == "ready":
            self.file_row.grid()
            self.progress.grid_remove()
            self.btn_secondary.grid_remove()
            self._set_options_enabled(True)
            self.btn_primary.configure(
                text="Crea ologramma", state="normal",
                fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._start,
            )
            self._refresh_estimate()

        elif state == "running":
            self._show_stage("preview")
            self.progress.grid()
            self.progress.set(0)
            self.btn_secondary.grid_remove()
            self._set_options_enabled(False)
            self.btn_primary.configure(
                text="Annulla", state="normal",
                fg_color=DANGER, hover_color="#DC2626", command=self._cancel,
            )

        elif state == "done":
            self.progress.set(1)
            self.btn_secondary.grid()
            self._set_options_enabled(True)
            self.btn_primary.configure(
                text="Nuova conversione", state="normal",
                fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._reset,
            )

    def _idle_hint(self):
        if engine.has_ffmpeg():
            return "Nessun video selezionato"
        return ("Nessun video selezionato  ·  installa ffmpeg per convertire "
                "circa 4 volte piu' in fretta")

    def _current_look(self):
        return engine.Look(
            background=BACKGROUND_PRESETS.get(self.background.get(), "none"),
            glow=GLOW_PRESETS.get(self.glow.get(), 0.0),
            autofit=bool(self.autofit.get()),
        )

    def _look_changed(self):
        """Un'opzione di resa e' cambiata: rigenera anteprima e stima."""
        if self.ui_state == "running" or not self.sources:
            return
        if self.ui_state == "done":
            self._reset()
        self._refresh_estimate()
        self._request_preview()

    def _show_stage(self, which):
        if which == "drop":
            self.preview_view.grid_remove()
            self.drop_view.grid()
        else:
            self.drop_view.grid_remove()
            self.preview_view.grid()

    def _set_placeholder(self, text):
        self.preview_label.configure(
            image="", text=text,
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED,
        )
        self.preview_image = None

    def _set_options_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in (self.quality, self.loop, self.background,
                       self.glow, self.autofit, self.btn_change):
            widget.configure(state=state)

    # -------------------------------------------------------------- azioni

    def _pick_source(self, *_):
        if getattr(self, "ui_state", None) == "running":
            return
        paths = filedialog.askopenfilenames(
            title="Scegli uno o piu' video",
            filetypes=[
                ("Video e modelli 3D", " ".join(
                    "*" + e for e in engine.VIDEO_EXTENSIONS + render3d.MODEL_EXTENSIONS)),
                ("Video", " ".join("*" + e for e in engine.VIDEO_EXTENSIONS)),
                ("Modelli 3D", " ".join("*" + e for e in render3d.MODEL_EXTENSIONS)),
                ("Tutti i file", "*.*"),
            ],
        )
        if paths:
            self._load_sources(list(paths))

    def _load_source(self, path):
        self._load_sources([path])

    def _load_sources(self, paths):
        loaded = []
        for path in paths:
            try:
                loaded.append((path, self._inspect(path)))
            except Exception as exc:
                if len(paths) == 1:
                    self.status.configure(text=str(exc), text_color=DANGER)
                    return

        if not loaded:
            self.status.configure(
                text="Nessuno dei file scelti e' un video leggibile.",
                text_color=DANGER,
            )
            return

        self.sources = [p for p, _ in loaded]
        self.source_path, self.source_info = loaded[0]
        self.outputs = self._suggest_outputs(self.sources)
        self.output_path = self.outputs[0]

        self._describe_selection(loaded)
        self._set_state("ready")
        self._request_preview()

    @staticmethod
    def _inspect(path):
        """Metadati della sorgente, che sia un video o un modello 3D."""
        if render3d.is_model(path):
            info = engine.model_info(path)
            info["kind"] = "model"
            info["frames"] = int(MODEL_SECONDS * MODEL_FPS)
            info["duration"] = MODEL_SECONDS
            return info
        info = engine.probe(path)
        info["kind"] = "video"
        return info

    def _describe_selection(self, loaded):
        first = os.path.basename(loaded[0][0])
        count = len(loaded)

        if count == 1:
            self.file_name.configure(
                text=first if len(first) <= 52 else first[:49] + "…")
            info = loaded[0][1]
            if info["kind"] == "model":
                self.file_meta.configure(
                    text=f"modello 3D  ·  {info['triangles']} triangoli  ·  "
                         f"giro di {human_time(MODEL_SECONDS)}  ·  "
                         f"{human_size(info['size_bytes'])}")
            else:
                self.file_meta.configure(
                    text=f"{info['width']}×{info['height']}  ·  "
                         f"{human_time(info['duration'])}  ·  {info['frames']} frame  ·  "
                         f"{human_size(info['size_bytes'])}")
            return

        label = first if len(first) <= 38 else first[:35] + "…"
        self.file_name.configure(text=f"{label}   +{count - 1} altri")
        self.file_meta.configure(
            text=f"{count} video  ·  "
                 f"{human_time(sum(i['duration'] for _, i in loaded))} in totale  ·  "
                 f"{human_size(sum(i['size_bytes'] for _, i in loaded))}")

    def _request_preview(self):
        """Calcola l'anteprima del risultato senza bloccare l'interfaccia."""
        self.preview_token += 1
        token = self.preview_token
        source = self.source_path

        self._show_stage("preview")
        self._set_placeholder("Generazione anteprima…")
        self.preview_caption.configure(text="")

        look = self._current_look()
        wants_loop = bool(self.loop.get())

        is_model = render3d.is_model(source)

        def work():
            try:
                warning = None
                if is_model:
                    frame = engine.preview_model(source, base_width=240, look=look)
                else:
                    if look.uses_motion:
                        # La differenza pretende un'inquadratura ferma e un
                        # soggetto che si sposti: meglio dirlo subito.
                        warning = engine.motion_suitability(source)["problem"]
                    if wants_loop:
                        engine.find_loop(source)
                    frame = engine.preview_frame(source, base_width=300, look=look)
            except engine.ConversionError as exc:
                self._post(self._on_preview_error, token, str(exc))
                return
            except Exception:
                self._post(self._on_preview_failed, token)
                return

            self._post(self._on_static_preview, token, frame)
            # Dopo l'anteprima, non prima: _on_static_preview riscrive la riga
            # di stato con la stima e cancellerebbe l'avviso.
            if warning:
                self._post(self._on_look_warning, token, warning)

        threading.Thread(target=work, daemon=True).start()

    def _on_static_preview(self, token, frame):
        if token != self.preview_token or self.ui_state == "running":
            return
        self._render_preview(frame)
        self.preview_caption.configure(text="Anteprima del risultato")
        self._refresh_estimate()

        # Un modello che non riconosce il soggetto restituisce una maschera
        # vuota, e il risultato sarebbe un video tutto nero: meglio dirlo ora
        # che dopo dieci minuti di conversione.
        # Un soggetto riconosciuto occupa sempre una porzione visibile del
        # fotogramma; contare i pixel accesi e' piu' affidabile del massimo,
        # che basta un solo pixel chiaro a far salire.
        look = self._current_look()
        lit = float((frame.max(axis=2) > 16).mean())
        if (look.removes_background and lit < 0.004
                and self.source_info.get("kind") != "model"):
            other = ("oggetto" if look.background == "person" else "persona")
            if look.uses_motion:
                other = "persona"
            self.status.configure(
                text=f"Il ritaglio non ha trovato il soggetto — prova "
                     f"\"Togli sfondo: {other}\"",
                text_color=DANGER,
            )

    def _on_look_warning(self, token, message):
        if token != self.preview_token:
            return
        self.status.configure(text=message, text_color=DANGER)

    def _on_preview_error(self, token, message):
        if token != self.preview_token:
            return
        self._set_placeholder("Anteprima non disponibile")
        self.status.configure(text=message, text_color=DANGER)

    def _on_preview_failed(self, token):
        if token != self.preview_token:
            return
        self._show_stage("drop")

    def _suggest_outputs(self, sources):
        taken = set()
        outputs = []
        for source in sources:
            path = self._suggest_output(source, taken)
            taken.add(path.lower())
            outputs.append(path)
        return outputs

    def _suggest_output(self, source, taken=()):
        base = os.path.splitext(os.path.basename(source))[0]
        candidate = os.path.join(OUTPUT_DIR, f"{base}_hologram.mp4")
        i = 2
        while os.path.exists(candidate) or candidate.lower() in taken:
            candidate = os.path.join(OUTPUT_DIR, f"{base}_hologram_{i}.mp4")
            i += 1
        return candidate

    def _refresh_estimate(self):
        if not self.source_info:
            return
        width = max(2, QUALITY_PRESETS[self.quality.get()] & ~1)

        if self.source_info.get("kind") == "model":
            side = 3 * width
            self.status.configure(
                text=f"Uscita: {side}×{side} px  ·  giro di "
                     f"{human_time(MODEL_SECONDS)}  ·  "
                     f"{os.path.basename(self.output_path)}",
                text_color=MUTED,
            )
            return

        source_w = self.source_info["width"]
        source_h = self.source_info["height"]
        if self.autofit.get():
            # Solo la cache: l'analisi costa quasi un secondo e bloccherebbe
            # la finestra. La stima si riallinea quando l'anteprima e' pronta.
            crop = engine.cached_bounds(self.source_path)
            if crop is not None:
                source_w, source_h = crop[2], crop[3]

        height = engine.scaled_height(source_w, source_h, width)
        side = engine.layout(height, width)

        parts = [f"Uscita: {side}×{side} px"]
        if self.loop.get():
            found = engine.cached_loop(self.source_path)
            if found is None:
                parts.append("ricerca del loop…")
            else:
                parts.append(f"loop {human_time(found.duration)} "
                             f"({100 * found.frames // self.source_info['frames']}%)")
        parts.append(os.path.basename(self.output_path))

        self.status.configure(text="  ·  ".join(parts), text_color=MUTED)

    def _start(self):
        if not self.sources or (self.worker and self.worker.is_alive()):
            return

        self.cancel_flag.clear()
        self.started_at = time.time()
        self._set_state("running")
        self.status.configure(text="Preparazione…", text_color=MUTED)
        self.preview_token += 1
        self.preview_caption.configure(text="")

        width = QUALITY_PRESETS[self.quality.get()]
        look = self._current_look()
        loop = bool(self.loop.get())
        jobs = list(zip(self.sources, self.outputs))

        last = {"progress": 0.0, "preview": 0.0}

        def work():
            results = []
            try:
                for position, (src, dst) in enumerate(jobs):
                    def on_progress(done, total, _phase, position=position):
                        now = time.time()
                        if done == total or now - last["progress"] >= 0.06:
                            last["progress"] = now
                            self._post(self._on_progress, position, done, total)

                    def on_preview(frame):
                        now = time.time()
                        if now - last["preview"] >= 0.25:
                            last["preview"] = now
                            self._post(self._on_preview, frame)

                    if render3d.is_model(src):
                        # Sul modello 3D lo sfondo e' gia' nero e il giro e'
                        # ciclico per costruzione: restano utili solo le luci.
                        results.append(engine.convert_model(
                            src, dst, base_width=width,
                            seconds=MODEL_SECONDS, fps=MODEL_FPS, turns=MODEL_TURNS,
                            look=engine.Look(glow=look.glow),
                            on_progress=on_progress, on_preview=on_preview,
                            should_cancel=self.cancel_flag.is_set,
                        ))
                    else:
                        results.append(engine.convert(
                            src, dst, base_width=width, look=look, loop=loop,
                            on_progress=on_progress, on_preview=on_preview,
                            should_cancel=self.cancel_flag.is_set,
                        ))
                self._post(self._on_done, results)
            except engine.ConversionCancelled:
                self._post(self._on_cancelled, results)
            except Exception as exc:
                self._post(self._on_error, exc)

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _post(self, callback, *args):
        """Esegue una callback sul thread dell'interfaccia, in sicurezza."""
        try:
            self.after(0, callback, *args)
        except RuntimeError:
            pass  # finestra gia' chiusa

    def _on_close(self):
        self.cancel_flag.set()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=3.0)
        self.destroy()

    def _cancel(self):
        self.cancel_flag.set()
        self.btn_primary.configure(text="Annullamento…", state="disabled")

    def _reset(self):
        if self.sources:
            self.outputs = self._suggest_outputs(self.sources)
            self.output_path = self.outputs[0]
        self._set_state("ready")

    def _open_output_folder(self):
        target = self.output_path if self.output_path else OUTPUT_DIR
        folder = os.path.dirname(target)
        if os.path.isdir(folder):
            os.startfile(folder)

    def _change_theme(self, choice):
        ctk.set_appearance_mode({"Sistema": "system", "Chiaro": "light", "Scuro": "dark"}[choice])

    # ------------------------------------------------------------ callback

    def _on_progress(self, position, done, total):
        """Avanzamento complessivo: ogni file pesa uguale nella coda."""
        jobs = max(1, len(self.sources))
        within = min(done / total, 1.0) if total > 0 else 0.0
        fraction = (position + within) / jobs

        self.progress.set(fraction)

        elapsed = time.time() - self.started_at
        parts = []
        if jobs > 1:
            parts.append(f"File {position + 1} di {jobs}")
            self.file_name.configure(text=os.path.basename(self.sources[position]))
        parts.append(f"{int(fraction * 100)}%")
        if total > 0:
            parts.append(f"{done} di {total} frame")
        if fraction > 0.01:
            eta = elapsed / fraction - elapsed
            parts.append(f"{human_time(eta)} rimanenti")

        self.status.configure(text="  ·  ".join(parts), text_color=MUTED)

    def _on_preview(self, frame):
        self._render_preview(frame)
        self.preview_caption.configure(text="Anteprima dal vivo")

    def _render_preview(self, frame):
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        size = self._preview_size()
        photo = ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))

        # L'immagine precedente va rilasciata solo DOPO che il label punta a
        # quella nuova: CTkLabel.configure applica prima `text` e, se nel
        # frattempo la vecchia PhotoImage e' stata raccolta dal garbage
        # collector, Tk fallisce con 'image "pyimageN" doesn't exist'.
        self.preview_label.configure(image=photo, text="")
        self.preview_image = photo

    def _preview_size(self):
        available = min(self.stage.winfo_height() - 90, self.stage.winfo_width() - 60)
        return max(160, min(available, 380))

    def _on_done(self, results):
        elapsed = time.time() - self.started_at
        self._set_state("done")

        frames = sum(r["frames"] for r in results)
        size = sum(r["size_bytes"] for r in results)
        head = f"{len(results)} ologrammi creati" if len(results) > 1 else "Fatto"

        self.status.configure(
            text=f"{head} in {human_time(elapsed)}  ·  {frames} frame  ·  "
                 f"{human_size(size)}",
            text_color=SUCCESS,
        )
        self.preview_caption.configure(text=os.path.basename(results[-1]["output"]))
        self._restore_selection_label()

    def _on_cancelled(self, results=()):
        self._set_state("ready")
        done = len(results)
        self.status.configure(
            text=("Conversione annullata" if not done
                  else f"Annullata dopo {done} di {len(self.sources)} video"),
            text_color=MUTED,
        )
        self._restore_selection_label()

    def _restore_selection_label(self):
        """Rimette il nome della selezione dopo che la coda l'ha sostituito."""
        try:
            self._describe_selection([(p, engine.probe(p)) for p in self.sources])
        except Exception:
            pass

    def _on_error(self, exc):
        self._set_state("ready")
        self.status.configure(text=f"Errore: {exc}", text_color=DANGER)

    # -------------------------------------------------------- drag & drop

    def _enable_drag_and_drop(self):
        if TkinterDnD is None:
            self.drop_hint.configure(text="Fai clic per scegliere un video dal computer")
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            self.drop_hint.configure(text="Fai clic per scegliere un video dal computer")

    def _on_drop(self, event):
        if getattr(self, "ui_state", None) == "running":
            return
        accepted = engine.VIDEO_EXTENSIONS + render3d.MODEL_EXTENSIONS
        paths = [p for p in self.tk.splitlist(event.data)
                 if p.lower().endswith(accepted)]
        if paths:
            self._load_sources(paths)


def main():
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    HologramApp().mainloop()


if __name__ == "__main__":
    main()
