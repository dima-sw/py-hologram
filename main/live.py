"""Riproduzione dal vivo dell'ologramma, per la piramide collegata allo schermo.

E' la stessa pipeline della conversione, senza il passaggio dalla codifica: i
fotogrammi vanno diritti a schermo. Serve per installazioni e vetrine, dove il
contenuto gira da solo, e per vedere subito l'effetto senza aspettare un file.

Un modello 3D viene ridisegnato a ogni fotogramma, quindi la rotazione e' vera
e non un video preregistrato. Un video viene invece composto e ripetuto in
ciclo continuo.
"""

import time

import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageTk

import engine
import render3d

# Cadenza di riferimento quando la sorgente non ne impone una.
DEFAULT_FPS = 30.0

# Sotto questa dimensione la finestra non scende: quattro viste piu' il centro
# nero hanno bisogno di spazio per restare leggibili.
MIN_SIDE = 360


class _ModelSource:
    """Modello 3D ridisegnato dal vivo, un giro continuo."""

    def __init__(self, path, side, look, seconds, turns, elevation):
        self.view = max(60, side // 3)
        self.renderer = render3d.TurntableRenderer(path, size=self.view)
        self.processor = engine._LookProcessor(look) if look.glow > 0 else None
        self.seconds = max(0.5, float(seconds))
        self.turns = float(turns)
        self.elevation = float(elevation)
        self.canvas = np.zeros((self.view * 3, self.view * 3, 3), np.uint8)
        self.fps = DEFAULT_FPS

    def frame(self, elapsed):
        angle = 360.0 * self.turns * (elapsed % self.seconds) / self.seconds
        views = self.renderer.render_views(angle, self.elevation)
        if self.processor is not None:
            views = {k: self.processor._add_glow(v) for k, v in views.items()}
        return engine.compose_views(views, self.canvas)

    def close(self):
        self.renderer.close()


class _VideoSource:
    """Video composto fotogramma per fotogramma e ripetuto senza sosta."""

    def __init__(self, path, width, look, loop=False):
        info = engine.probe(path)
        self.path = path
        self.fps = info["fps"]

        self.crop = engine.content_bounds(path) if look.autofit else None
        source_w = self.crop[2] if self.crop else info["width"]
        source_h = self.crop[3] if self.crop else info["height"]

        self.width = max(2, int(width) & ~1)
        self.height = engine.scaled_height(source_w, source_h, self.width)
        self.side = engine.layout(self.height, self.width)

        self.trim = None
        found = engine.find_loop(path, fps=self.fps) if loop else None
        if found is not None:
            self.trim = (found.start, found.end)

        self.processor = (engine._LookProcessor(
            look, source=path, size=(self.width, self.height))
            if look.touches_pixels else None)

        self.canvas = np.zeros((self.side, self.side, 3), np.uint8)
        self._frames = None
        self._last = None
        self._restart()

    def _restart(self):
        self._close_reader()
        self._reader = engine._open_reader(
            self.path, self.width, self.height, True,
            crop=self.crop, trim=self.trim)
        self._frames = iter(self._reader)

    def _close_reader(self):
        reader = getattr(self, "_reader", None)
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass
        self._reader = None

    def frame(self, _elapsed):
        try:
            frame = next(self._frames)
        except StopIteration:
            self._restart()
            try:
                frame = next(self._frames)
            except StopIteration:
                # Nessun fotogramma leggibile: si tiene l'ultimo mostrato.
                return self._last if self._last is not None else self.canvas

        if self.processor is not None:
            frame = self.processor.apply(frame)

        self._last = engine.compose_frame(frame, self.canvas)
        return self._last

    def close(self):
        self._close_reader()


class LiveWindow(ctk.CTkToplevel):
    """Finestra che riproduce l'ologramma senza produrre alcun file.

    Pensata per stare a schermo intero sul monitor su cui poggia la piramide:
    Esc esce, F alterna schermo intero, barra spaziatrice mette in pausa.
    """

    def __init__(self, master, source, look, settings, fullscreen=True,
                 on_error=None):
        super().__init__(master)

        self.source_path = source
        self.on_error = on_error
        self.paused = False
        self.started_at = time.perf_counter()
        self.paused_at = 0.0
        self._photo = None
        self._after_id = None
        self._closed = False

        self.title("Hologram Studio · dal vivo")
        self.configure(fg_color="#000000")
        self.geometry("900x900")
        self.minsize(MIN_SIDE, MIN_SIDE)

        self.canvas = ctk.CTkCanvas(self, bg="#000000", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._image_id = self.canvas.create_image(0, 0, anchor="center")

        self.hint = ctk.CTkLabel(
            self, text="Esc esce   ·   F schermo intero   ·   Spazio mette in pausa",
            font=ctk.CTkFont("Segoe UI", 13), text_color="#8A8FA3", fg_color="#000000",
        )
        self.hint.place(relx=0.5, rely=0.97, anchor="s")
        self.after(4000, self._hide_hint)

        for key in ("<Escape>",):
            self.bind(key, lambda _e: self.close())
        for key in ("<f>", "<F>", "<F11>"):
            self.bind(key, lambda _e: self.toggle_fullscreen())
        self.bind("<space>", lambda _e: self.toggle_pause())
        self.protocol("WM_DELETE_WINDOW", self.close)

        try:
            self.source = self._build_source(source, look, settings)
        except Exception as exc:
            self.after(0, lambda: self._fail(exc))
            return

        self.interval = max(10, int(1000.0 / max(1.0, self.source.fps)))

        if fullscreen:
            self.after(150, lambda: self.attributes("-fullscreen", True))
        self.after(120, self._focus)
        self._tick()

    # -- costruzione

    def _build_source(self, path, look, settings):
        if render3d.is_model(path):
            return _ModelSource(
                path, 900, look,
                seconds=settings.get("model_seconds"),
                turns=settings.get("model_turns"),
                elevation=settings.get("model_elevation"),
            )
        return _VideoSource(path, 300, look, loop=bool(settings.get("loop")))

    def _focus(self):
        self.lift()
        self.focus_force()

    def _hide_hint(self):
        if not self._closed:
            self.hint.place_forget()

    # -- riproduzione

    def _tick(self):
        if self._closed:
            return

        started = time.perf_counter()

        if not self.paused:
            try:
                frame = self.source.frame(started - self.started_at)
                self._show(frame)
            except Exception as exc:
                self._fail(exc)
                return

        # after() conta il ritardo a partire da adesso, quindi sommare
        # l'intervallo pieno allungherebbe il periodo del tempo di calcolo e
        # la riproduzione andrebbe sistematicamente piu' lenta del dovuto.
        spent = (time.perf_counter() - started) * 1000.0
        self._after_id = self.after(max(1, int(self.interval - spent)), self._tick)

    def _show(self, frame):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        side = max(1, min(width, height))

        if frame.shape[0] != side:
            interpolation = (cv2.INTER_AREA if frame.shape[0] > side
                             else cv2.INTER_LINEAR)
            frame = cv2.resize(frame, (side, side), interpolation=interpolation)

        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Il riferimento va tenuto: Tk non possiede l'immagine e senza questo
        # il garbage collector la libera prima che venga disegnata.
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.itemconfigure(self._image_id, image=self._photo)
        self.canvas.coords(self._image_id, width // 2, height // 2)

    # -- comandi

    def toggle_pause(self):
        if self.paused:
            self.started_at += time.perf_counter() - self.paused_at
        else:
            self.paused_at = time.perf_counter()
        self.paused = not self.paused

    def toggle_fullscreen(self):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def _fail(self, exc):
        if self.on_error is not None:
            self.on_error(str(exc))
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True

        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass

        source = getattr(self, "source", None)
        if source is not None:
            try:
                source.close()
            except Exception:
                pass

        self.destroy()
