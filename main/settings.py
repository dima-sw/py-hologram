"""Impostazioni dell'applicazione e finestra per modificarle.

Le preferenze vivono in un file JSON nella cartella dell'utente, cosi'
sopravvivono alla chiusura. Un valore illeggibile o fuori dai valori ammessi
viene sostituito dal predefinito invece di far fallire l'avvio: un file di
configurazione rovinato non deve impedire di usare il programma.
"""

import json
import os

import customtkinter as ctk

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".hologram_studio.json")

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

# Oltre 0,5 il bagliore brucia i punti piu' chiari del soggetto.
GLOW_PRESETS = {
    "No": 0.0,
    "Lieve": 0.3,
    "Intenso": 0.5,
}

# Un fotogramma ogni N viene segmentato davvero. Le percentuali sono la
# precisione misurata su una clip con maschera nota, rispetto al valore 1.
STRIDE_PRESETS = {
    "Ogni fotogramma": 1,
    "Uno su 2": 2,
    "Uno su 3": 3,
    "Uno su 4": 4,
}

THEMES = {"Sistema": "system", "Chiaro": "light", "Scuro": "dark"}

DEFAULTS = {
    "quality": "Media",
    "background": "Originale",
    "glow": "No",
    "autofit": False,
    "loop": False,
    "stride": "Ogni fotogramma",
    "output_dir": "",
    "model_seconds": 8.0,
    "model_turns": 1.0,
    "model_elevation": 16.0,
    "theme": "Sistema",
}

_CHOICES = {
    "quality": QUALITY_PRESETS,
    "background": BACKGROUND_PRESETS,
    "glow": GLOW_PRESETS,
    "stride": STRIDE_PRESETS,
    "theme": THEMES,
}


class Settings:
    """Preferenze dell'utente, con lettura e scrittura su disco."""

    def __init__(self, **values):
        self._values = dict(DEFAULTS)
        self.update(values)

    # -- accesso

    def __getattr__(self, name):
        try:
            return self.__dict__["_values"][name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def get(self, name):
        return self._values.get(name, DEFAULTS.get(name))

    def update(self, values):
        for key, value in (values or {}).items():
            if key not in DEFAULTS:
                continue
            self._values[key] = self._sanitised(key, value)

    def as_dict(self):
        return dict(self._values)

    def reset(self):
        self._values = dict(DEFAULTS)

    @staticmethod
    def _sanitised(key, value):
        """Riporta nei limiti un valore proveniente dal disco."""
        default = DEFAULTS[key]

        if key in _CHOICES:
            return value if value in _CHOICES[key] else default
        if isinstance(default, bool):
            return bool(value)
        if isinstance(default, float):
            try:
                number = float(value)
            except (TypeError, ValueError):
                return default
            limits = {"model_seconds": (1.0, 120.0),
                      "model_turns": (0.1, 20.0),
                      "model_elevation": (-80.0, 80.0)}
            low, high = limits.get(key, (float("-inf"), float("inf")))
            return min(max(number, low), high)
        if key == "output_dir":
            return value if isinstance(value, str) else default
        return value

    # -- persistenza

    @classmethod
    def load(cls, path=CONFIG_PATH):
        try:
            with open(path, encoding="utf-8") as handle:
                return cls(**json.load(handle))
        except (OSError, ValueError):
            return cls()

    def save(self, path=CONFIG_PATH):
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self._values, handle, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False


class SettingsDialog(ctk.CTkToplevel):
    """Finestra con tutte le impostazioni, raggruppate per argomento."""

    def __init__(self, master, settings, palette, on_change,
                 provider_label="", output_default=""):
        super().__init__(master)

        self.settings = settings
        self.palette = palette
        self.on_change = on_change
        self.output_default = output_default
        self.provider_label = provider_label

        self.title("Impostazioni")
        self.geometry("560x640")
        self.minsize(520, 520)
        self.configure(fg_color=palette["bg"])
        self.transient(master)

        self._build(provider_label)

        # Su Windows la finestra figlia va alzata dopo che e' stata disegnata,
        # altrimenti resta dietro a quella principale.
        self.after(120, self._raise)

    def _raise(self):
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    # -- costruzione

    def _build(self, provider_label):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=18, pady=(18, 8))
        body.grid_columnconfigure(0, weight=1)

        row = 0
        row = self._section(body, row, "Uscita", [
            ("Qualità", self._option("quality", list(QUALITY_PRESETS))),
            ("Cartella", self._folder_row),
        ])
        row = self._section(body, row, "Aspetto", [
            ("Sfondo", self._option("background", list(BACKGROUND_PRESETS))),
            ("Bagliore", self._option("glow", list(GLOW_PRESETS))),
            ("Riempi la faccia", self._switch("autofit")),
            ("Loop perfetto", self._switch("loop")),
        ])
        row = self._section(body, row, "Rimozione sfondo", [
            ("Acceleratore", self._static(provider_label)),
            ("Segmentazione", self._option("stride", list(STRIDE_PRESETS))),
        ])
        row = self._section(body, row, "Modelli 3D", [
            ("Durata (secondi)", self._number("model_seconds", 1, 60)),
            ("Giri completi", self._number("model_turns", 0.5, 5, step=0.5)),
            ("Inclinazione (gradi)", self._number("model_elevation", -60, 60, step=2)),
        ])
        self._section(body, row, "Aspetto dell'app", [
            ("Tema", self._option("theme", list(THEMES))),
        ])

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer, text="Ripristina predefiniti", width=180, height=38,
            corner_radius=10, font=ctk.CTkFont("Segoe UI", 12),
            fg_color=self.palette["card"], hover_color=self.palette["card_soft"],
            text_color=self.palette["text"], border_width=1,
            border_color=self.palette["border"], command=self._reset,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer, text="Chiudi", width=120, height=38, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=self.palette["accent"], hover_color=self.palette["accent_hover"],
            text_color="#FFFFFF", command=self._close,
        ).grid(row=0, column=1, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self._close)

    def _section(self, parent, row, title, entries):
        ctk.CTkLabel(
            parent, text=title.upper(), anchor="w",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=self.palette["muted"],
        ).grid(row=row, column=0, sticky="ew", pady=(14 if row else 0, 6))
        row += 1

        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=self.palette["card"],
                            border_width=1, border_color=self.palette["border"])
        card.grid(row=row, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        for index, (label, factory) in enumerate(entries):
            ctk.CTkLabel(
                card, text=label, anchor="w", font=ctk.CTkFont("Segoe UI", 13),
                text_color=self.palette["text"],
            ).grid(row=index, column=0, sticky="w", padx=(16, 12), pady=10)
            factory(card).grid(row=index, column=1, sticky="e", padx=(0, 16), pady=10)

        return row + 1

    # -- controlli

    def _apply(self, key, value):
        self.settings.update({key: value})
        self.settings.save()
        if self.on_change:
            self.on_change(key)

    def _option(self, key, values):
        def factory(parent):
            widget = ctk.CTkOptionMenu(
                parent, values=values, width=216, height=32, corner_radius=9,
                font=ctk.CTkFont("Segoe UI", 12),
                fg_color=self.palette["card_soft"], button_color=self.palette["card_soft"],
                button_hover_color=self.palette["border"], text_color=self.palette["text"],
                dropdown_font=ctk.CTkFont("Segoe UI", 12),
                command=lambda value, k=key: self._apply(k, value),
            )
            widget.set(self.settings.get(key))
            return widget
        return factory

    def _switch(self, key):
        def factory(parent):
            widget = ctk.CTkSwitch(
                parent, text="", width=48, progress_color=self.palette["accent"],
                button_color="#FFFFFF",
                command=lambda k=key: self._apply(k, bool(widget.get())),
            )
            widget.select() if self.settings.get(key) else widget.deselect()
            return widget
        return factory

    def _number(self, key, low, high, step=1):
        def factory(parent):
            holder = ctk.CTkFrame(parent, fg_color="transparent")
            value = ctk.CTkLabel(
                holder, text=self._format(self.settings.get(key)), width=54,
                font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color=self.palette["text"],
            )

            def nudge(delta):
                current = float(self.settings.get(key)) + delta
                current = min(max(current, low), high)
                self._apply(key, current)
                value.configure(text=self._format(self.settings.get(key)))

            for column, (text, delta) in enumerate((("−", -step), ("+", step))):
                ctk.CTkButton(
                    holder, text=text, width=34, height=30, corner_radius=8,
                    font=ctk.CTkFont("Segoe UI", 15),
                    fg_color=self.palette["card_soft"],
                    hover_color=self.palette["border"], text_color=self.palette["text"],
                    command=lambda d=delta: nudge(d),
                ).grid(row=0, column=column * 2, padx=2)
            value.grid(row=0, column=1)
            return holder
        return factory

    def _static(self, text):
        def factory(parent):
            return ctk.CTkLabel(
                parent, text=text or "non disponibile",
                font=ctk.CTkFont("Segoe UI", 12), text_color=self.palette["muted"],
            )
        return factory

    def _folder_row(self, parent):
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        current = self.settings.get("output_dir") or self.output_default
        label = ctk.CTkLabel(
            holder, text=self._shorten(current), width=180, anchor="e",
            font=ctk.CTkFont("Segoe UI", 11), text_color=self.palette["muted"],
        )
        label.grid(row=0, column=0, padx=(0, 8))

        def choose():
            from tkinter import filedialog
            chosen = filedialog.askdirectory(
                title="Cartella di destinazione",
                initialdir=current or os.path.expanduser("~"), parent=self)
            if chosen:
                self._apply("output_dir", chosen)
                label.configure(text=self._shorten(chosen))

        ctk.CTkButton(
            holder, text="Scegli…", width=80, height=30, corner_radius=8,
            font=ctk.CTkFont("Segoe UI", 12), fg_color=self.palette["card_soft"],
            hover_color=self.palette["border"], text_color=self.palette["text"],
            command=choose,
        ).grid(row=0, column=1)
        return holder

    @staticmethod
    def _format(value):
        number = float(value)
        return str(int(number)) if number == int(number) else f"{number:.1f}"

    @staticmethod
    def _shorten(path, limit=30):
        if not path:
            return "predefinita"
        return path if len(path) <= limit else "…" + path[-(limit - 1):]

    # -- azioni

    def _reset(self):
        self.settings.reset()
        self.settings.save()
        if self.on_change:
            self.on_change(None)
        # Il modo piu' sicuro di riflettere valori cambiati tutti insieme e'
        # ridisegnare la finestra da capo.
        for child in self.winfo_children():
            child.destroy()
        self._build(self.provider_label)

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
