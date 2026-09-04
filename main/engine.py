"""Motore di conversione video -> ologramma piramidale a 4 lati.

Architettura della pipeline (misurata ~5x piu' veloce dell'implementazione
precedente):

  ffmpeg (decodifica + ridimensionamento, multi-thread)
      -> composizione con cv2.rotate (SIMD)
          -> scrittura su un thread dedicato

Il video non viene mai caricato interamente in memoria: i frame scorrono uno
alla volta, quindi la RAM usata non dipende dalla durata del filmato.

Se ffmpeg non e' installato si ricade su OpenCV, che e' piu' lento ma non
richiede nulla di esterno.
"""

import math
import os
import queue
import shutil
import subprocess
import threading

import cv2
import numpy as np

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".wmv", ".m4v", ".mpg", ".mpeg", ".webm")

FFMPEG = shutil.which("ffmpeg")

# Su Windows evita che ogni sottoprocesso apra una finestra di console.
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

_CCW = cv2.ROTATE_90_COUNTERCLOCKWISE
_CW = cv2.ROTATE_90_CLOCKWISE
_R180 = cv2.ROTATE_180

# Numero di canvas che ruotano tra composizione e scrittura. Con un solo
# buffer i due stadi non si sovrappongono; oltre i quattro non si guadagna.
_BUFFER_COUNT = 4


class ConversionCancelled(Exception):
    """Sollevata quando l'utente annulla la conversione in corso."""


class ConversionError(Exception):
    """Errore non recuperabile durante la conversione."""


def has_ffmpeg():
    """True se il percorso veloce (ffmpeg) e' disponibile."""
    return FFMPEG is not None


# --------------------------------------------------------------- geometria

def layout(frame_rows, frame_cols):
    """Dimensione del canvas e posizione delle quattro viste.

    Le quattro copie del frame sono disposte a croce attorno a un centro nero.
    Il lato viene reso pari: gli encoder H.264 in yuv420p rifiutano le
    dimensioni dispari.
    """
    side = 2 * frame_rows + frame_cols
    side += side % 2
    return side


def new_canvas(frame):
    """Crea il canvas quadrato nero che ospita le quattro viste."""
    rows, cols = frame.shape[:2]
    side = layout(rows, cols)
    return np.zeros((side, side, frame.shape[2]), dtype=np.uint8)


def compose_frame(frame, canvas):
    """Dispone `frame` sui quattro lati di `canvas` e lo restituisce.

    Il canvas viene riusato tra un frame e l'altro: le quattro regioni sono
    sempre le stesse e vengono sovrascritte, quindi non serve azzerarlo.

    cv2.rotate e' vettorizzato e batte di circa il doppio il kernel Numba
    equivalente, senza pagare i secondi di compilazione JIT al primo avvio.
    """
    r, c = frame.shape[:2]

    canvas[0:r, r:r + c] = frame                            # alto
    canvas[r:r + c, 0:r] = cv2.rotate(frame, _CCW)          # sinistra
    canvas[r + c:r + c + r, r:r + c] = cv2.rotate(frame, _R180)   # basso
    canvas[r:r + c, r + c:r + c + r] = cv2.rotate(frame, _CW)     # destra

    return canvas


def scaled_height(src_width, src_height, width):
    """Altezza corrispondente a `width` mantenendo le proporzioni."""
    return max(1, int(round(src_height * (width / float(src_width)))))


def resize_to_width(image, width):
    """Ridimensiona mantenendo le proporzioni.

    Per riduzioni forti INTER_AREA e' molto costoso (opera su tutti i pixel
    sorgente), quindi ci si avvicina prima con pyrDown, che dimezza a ogni
    passo applicando un filtro gaussiano.
    """
    src_h, src_w = image.shape[:2]
    if src_w == width:
        return image

    height = scaled_height(src_w, src_h, width)

    h, w = src_h, src_w
    while w >= width * 2 and w > 2 and h > 2:
        image = cv2.pyrDown(image)
        h, w = image.shape[:2]

    interpolation = cv2.INTER_AREA if width < w else cv2.INTER_LINEAR
    return cv2.resize(image, (width, height), interpolation=interpolation)


# ---------------------------------------------------------- segmentazione AI

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# Modelli U^2-Net in formato ONNX. Il primo e' specializzato sulle persone e
# le ritaglia molto meglio; il secondo e' generico e circa doppio in velocita'.
SEGMENTATION_MODELS = {
    "person": "u2net_human_seg.onnx",
    "object": "u2netp.onnx",
}

MODEL_SOURCE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"

_U2NET_MEAN = np.array([0.485, 0.456, 0.406], "f4")
_U2NET_STD = np.array([0.229, 0.224, 0.225], "f4")
_U2NET_SIDE = 320


def model_path(kind):
    return os.path.join(MODELS_DIR, SEGMENTATION_MODELS[kind])


def has_model(kind):
    return kind in SEGMENTATION_MODELS and os.path.exists(model_path(kind))


def available_models():
    return [k for k in SEGMENTATION_MODELS if has_model(k)]


# Acceleratori provati in ordine. DirectML sfrutta qualunque GPU su Windows
# senza bisogno di CUDA: sui modelli U^2-Net rende circa dieci volte la CPU.
_PROVIDER_ORDER = ("DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider")


def segmentation_provider():
    """Acceleratore che verrebbe usato, o None se manca onnxruntime."""
    try:
        import onnxruntime as ort
    except ImportError:
        return None
    available = ort.get_available_providers()
    for name in _PROVIDER_ORDER:
        if name in available:
            return name
    return available[0] if available else None


def provider_label(name):
    return {
        "DmlExecutionProvider": "GPU (DirectML)",
        "CUDAExecutionProvider": "GPU (CUDA)",
        "CPUExecutionProvider": "CPU",
    }.get(name or "", "non disponibile")


class _Segmenter:
    """Ritaglia il soggetto con U^2-Net, fotogramma per fotogramma.

    Usa la GPU quando onnxruntime la espone, altrimenti la CPU. E' comunque
    la parte piu' lenta della pipeline, ma su GPU passa da un paio di
    fotogrammi al secondo a qualche decina.
    """

    # Quattro thread rendono piu' di sei: oltre quel punto i thread litigano
    # fra loro e il tempo per fotogramma peggiora (misurato). Vale solo per la
    # CPU: sull'acceleratore il parametro e' ignorato.
    _THREADS = 4

    # Peso del fotogramma corrente nella media con quello precedente. La
    # maschera calcolata su ogni fotogramma da sola "sfarfalla" sui bordi.
    _SMOOTHING = 0.7

    def __init__(self, kind, feather=1.2, stride=1):
        path = model_path(kind)
        if not os.path.exists(path):
            raise ConversionError(
                f"Manca il modello {SEGMENTATION_MODELS[kind]}. "
                f"Scaricalo da {MODEL_SOURCE}{SEGMENTATION_MODELS[kind]} "
                f"e mettilo nella cartella models/."
            )

        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise ConversionError(
                "Per rimuovere lo sfondo serve onnxruntime: "
                "pip install onnxruntime"
            ) from exc

        options = ort.SessionOptions()
        options.log_severity_level = 3
        options.intra_op_num_threads = self._THREADS
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        available = ort.get_available_providers()
        wanted = [p for p in _PROVIDER_ORDER if p in available] or available
        try:
            self._session = ort.InferenceSession(path, options, providers=wanted)
        except Exception:
            # Un acceleratore puo' essere elencato e poi non inizializzarsi:
            # meglio ripiegare sulla CPU che fallire la conversione.
            self._session = ort.InferenceSession(
                path, options, providers=["CPUExecutionProvider"])

        self.provider = (self._session.get_providers() or ["CPUExecutionProvider"])[0]
        self._input = self._session.get_inputs()[0].name
        self._feather = feather

        # Un fotogramma ogni `stride` viene segmentato davvero; gli altri
        # riusano la maschera precedente. Il soggetto si sposta di poco fra
        # un fotogramma e il successivo, quindi il costo in qualita' e'
        # contenuto e il guadagno in tempo e' lineare.
        self._stride = max(1, int(stride))
        self._counter = 0
        self._cached = None
        self._previous = None

    def _prepare(self, frame):
        small = cv2.resize(frame, (_U2NET_SIDE, _U2NET_SIDE),
                           interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype("f4")
        rgb /= max(float(rgb.max()), 1.0)
        rgb = (rgb - _U2NET_MEAN) / _U2NET_STD
        return np.ascontiguousarray(rgb.transpose(2, 0, 1)[None])

    def alpha(self, frame):
        """Maschera 0..1 delle dimensioni del frame."""
        reuse = self._cached is not None and self._counter % self._stride != 0
        self._counter += 1
        if reuse:
            return self._cached

        self._cached = self._infer(frame)
        return self._cached

    def _infer(self, frame):
        prediction = self._session.run(None, {self._input: self._prepare(frame)})[0]
        mask = prediction[0, 0]

        low, high = float(mask.min()), float(mask.max())
        mask = (mask - low) / (high - low) if high > low else np.zeros_like(mask)

        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_LINEAR)
        if self._feather > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), self._feather)

        if self._previous is not None:
            mask = self._SMOOTHING * mask + (1.0 - self._SMOOTHING) * self._previous
        self._previous = mask

        return mask

    def reset(self):
        self._previous = None
        self._cached = None
        self._counter = 0


# ------------------------------------------- rimozione sfondo per differenza

# Fotogrammi campionati per ricostruire lo sfondo. La mediana per pixel
# funziona finche' il soggetto passa su ciascun punto meno della meta' del
# tempo: sopra quella soglia lo sfondo "assorbe" il soggetto.
_PLATE_SAMPLES = 41

# Soglie della differenza in Lab, tarate su una clip con maschera nota
# (IoU 0,79). Quella alta innesca, quella bassa fa crescere la regione.
_MOTION_HIGH = 10.0
_MOTION_LOW = 8.0

# Un pixel piu' scuro con lo stesso colore e' quasi sempre un'ombra, non il
# soggetto: il calo di luminosita' pesa molto meno del suo aumento.
_MOTION_DARK_WEIGHT = 0.3

_plate_cache = {}


def _sample_frames(src, width, height, samples):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise ConversionError("Impossibile aprire il video sorgente.")
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        positions = ([int(total * i / samples) for i in range(samples)]
                     if total > samples else [0])
        frames = []
        for position in positions:
            if total > samples:
                cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, frame = cap.read()
            if ok and frame is not None:
                frames.append(cv2.resize(frame, (width, height),
                                         interpolation=cv2.INTER_AREA))
    finally:
        cap.release()
    return frames


def background_plate(src, width, height, samples=_PLATE_SAMPLES):
    """Ricostruisce lo sfondo come mediana per pixel dei fotogrammi.

    La mediana, non la media: cosi' il soggetto che attraversa la scena non
    lascia scia, purche' non stazioni troppo a lungo sullo stesso punto.
    """
    try:
        key = (os.path.abspath(src), os.path.getmtime(src), width, height, samples)
    except OSError:
        key = None
    if key is not None and key in _plate_cache:
        return _plate_cache[key]

    frames = _sample_frames(src, width, height, samples)
    if len(frames) < 5:
        raise ConversionError(
            "Il video e' troppo corto per ricostruire lo sfondo per differenza."
        )

    plate = np.median(np.stack(frames).astype(np.float32), axis=0).astype(np.uint8)

    if key is not None:
        if len(_plate_cache) > 8:
            _plate_cache.clear()
        _plate_cache[key] = plate
    return plate


def camera_shift(src, samples=12, side=256):
    """Spostamento tipico dell'inquadratura, in pixel su un lato di 256.

    Sotto i due pixel la camera si puo' considerare ferma; sopra, la
    ricostruzione dello sfondo per differenza non regge.
    """
    frames = _sample_frames(src, side, side, samples)
    previous = None
    shifts = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if previous is not None:
            (dx, dy), _ = cv2.phaseCorrelate(previous, gray)
            shifts.append(math.hypot(dx, dy))
        previous = gray
    return float(np.median(shifts)) if shifts else 0.0


class _MotionSegmenter:
    """Separa il soggetto confrontando ogni fotogramma con lo sfondo ricostruito.

    Rispetto alla segmentazione neurale e' circa sessanta volte piu' rapida e
    non richiede alcun modello, ma pretende che l'inquadratura sia ferma. In
    compenso tutto cio' che non si muove diventa sfondo per definizione,
    comprese le statue e gli arredi che un modello di salienza terrebbe.
    """

    _SMOOTHING = 0.7

    def __init__(self, plate, feather=1.2, close_ratio=0.02):
        self._plate_lab = cv2.cvtColor(plate, cv2.COLOR_BGR2Lab).astype(np.float32)
        self._feather = feather
        self._close_ratio = close_ratio
        self._previous = None

    def _distance(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2Lab).astype(np.float32)
        delta = lab - self._plate_lab
        lightness = delta[:, :, 0]
        weight = np.where(lightness < 0, _MOTION_DARK_WEIGHT, 1.0)
        return np.sqrt((weight * lightness) ** 2
                       + delta[:, :, 1] ** 2 + delta[:, :, 2] ** 2)

    @staticmethod
    def _fill_holes(mask):
        """Una cavita' circondata dal soggetto e' soggetto."""
        flooded = mask.copy()
        border = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), np.uint8)
        cv2.floodFill(flooded, border, (0, 0), 255)
        return mask | cv2.bitwise_not(flooded)

    @staticmethod
    def _drop_specks(mask, relative=0.03, absolute=0.0008):
        """Scarta le macchie molto piu' piccole del soggetto.

        Il rumore di compressione sui bordi netti dello sfondo supera ogni
        tanto la soglia e lascia coriandoli sparsi. Un soggetto spezzato in
        due pezzi comparabili viene invece conservato.
        """
        count, labels, stats, _ = cv2.connectedComponentsWithStats(
            (mask > 0).astype(np.uint8), connectivity=8)
        if count <= 2:
            return mask

        areas = stats[1:, cv2.CC_STAT_AREA]
        floor = max(areas.max() * relative, mask.size * absolute)
        keep = 1 + np.flatnonzero(areas >= floor)
        return np.isin(labels, keep).astype(np.uint8) * 255

    def alpha(self, frame):
        distance = self._distance(frame)

        # Isteresi: si tengono solo le regioni oltre la soglia bassa che
        # contengono almeno un pixel oltre quella alta. Una soglia sola
        # sbriciolerebbe il soggetto o inghiottirebbe il rumore.
        seeds = (distance > _MOTION_HIGH).astype(np.uint8)
        grown = (distance > _MOTION_LOW).astype(np.uint8)
        count, labels = cv2.connectedComponents(grown, connectivity=8)
        keep = np.unique(labels[seeds > 0])
        keep = keep[keep > 0]
        mask = np.isin(labels, keep).astype(np.uint8) * 255

        size = max(3, int(frame.shape[1] * self._close_ratio) | 1)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
        mask = self._fill_holes(mask)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        mask = self._drop_specks(mask)

        alpha = mask.astype(np.float32) / 255.0
        if self._feather > 0:
            alpha = cv2.GaussianBlur(alpha, (0, 0), self._feather)

        if self._previous is not None:
            alpha = self._SMOOTHING * alpha + (1.0 - self._SMOOTHING) * self._previous
        self._previous = alpha
        return alpha


def motion_suitability(src, width=300):
    """Dice se la rimozione per differenza ha senso su questo video.

    Restituisce lo spostamento della camera, la quota di fotogramma
    classificata come soggetto e un messaggio quando qualcosa non torna.
    """
    info = probe(src)
    height = scaled_height(info["width"], info["height"], width)

    shift = camera_shift(src)
    plate = background_plate(src, width, height)

    segmenter = _MotionSegmenter(plate)
    frames = _sample_frames(src, width, height, 6)
    coverage = [float((segmenter.alpha(f) > 0.5).mean()) for f in frames]
    segmenter.reset() if hasattr(segmenter, "reset") else None
    foreground = float(np.median(coverage)) if coverage else 0.0

    problem = None
    if shift > 2.0:
        problem = (f"L'inquadratura si muove ({shift:.1f} px): per la differenza "
                   f"serve una camera ferma su cavalletto.")
    elif foreground > 0.35:
        problem = ("Lo sfondo ricostruito non e' affidabile: il soggetto resta "
                   "troppo fermo e vi e' finito dentro.")
    elif foreground < 0.005:
        problem = "Non si muove quasi nulla: non c'e' un soggetto da separare."

    return {"camera_shift": shift, "foreground": foreground, "problem": problem}


# ------------------------------------------------------------------ aspetto

BACKGROUND_MODES = ("none", "motion", "person", "object", "black", "green")


class Look:
    """Trattamento applicato a ogni frame prima della composizione.

    background  "none"   lascia il frame com'e'
                "motion" ricostruisce lo sfondo e lo sottrae (camera ferma)
                "person" ritaglia la persona con la segmentazione AI
                "object" come sopra, con il modello generico
                "black"  spegne il fondo gia' scuro portandolo a nero pieno
                "green"  rimuove uno sfondo verde (green screen)
    glow        0..1, bagliore attorno alle parti luminose
    autofit     ritaglia il vuoto attorno al soggetto per riempire la faccia
    """

    def __init__(self, background="none", glow=0.0, autofit=False,
                 black_level=48, green_spill=True, segment_stride=1):
        self.background = background if background in BACKGROUND_MODES else "none"
        self.glow = max(0.0, min(1.0, float(glow)))
        self.autofit = bool(autofit)
        self.black_level = int(black_level)
        self.green_spill = bool(green_spill)
        self.segment_stride = max(1, int(segment_stride))

    @property
    def touches_pixels(self):
        return self.background != "none" or self.glow > 0

    @property
    def uses_segmentation(self):
        return self.background in ("person", "object")

    @property
    def uses_motion(self):
        return self.background == "motion"

    @property
    def removes_background(self):
        return self.uses_segmentation or self.uses_motion

    def __repr__(self):
        return (f"Look(background={self.background!r}, glow={self.glow}, "
                f"autofit={self.autofit})")


class _LookProcessor:
    """Applica un Look ai frame, riusando tabelle e buffer.

    Lavora sul frame gia' ridimensionato (poche centinaia di pixel di lato):
    e' quattro volte piu' economico che agire sul canvas composto.
    """

    # Tinte considerate verdi in HSV (OpenCV usa H in 0..179).
    _GREEN_LO = np.array([35, 60, 40], np.uint8)
    _GREEN_HI = np.array([85, 255, 255], np.uint8)

    def __init__(self, look, source=None, size=None):
        self.look = look
        self._fade = self._build_fade(look.black_level)
        self._segmenter = (_Segmenter(look.background, stride=look.segment_stride)
                           if look.uses_segmentation else None)

        self._motion = None
        if look.uses_motion:
            if source is None or size is None:
                raise ConversionError(
                    "La rimozione per differenza ha bisogno del video sorgente.")
            self._motion = _MotionSegmenter(
                background_plate(source, size[0], size[1]))

    @staticmethod
    def _build_fade(level):
        """Tabella luminanza -> fattore, con raccordo morbido.

        Sotto un quarto della soglia il pixel diventa nero pieno, sopra la
        soglia resta intatto: il taglio netto lascerebbe bordi seghettati.
        """
        low = max(1, level // 4)
        high = max(low + 1, level)
        x = np.arange(256, dtype=np.float32)
        fade = np.clip((x - low) / float(high - low), 0.0, 1.0)
        return (fade * 255).astype(np.uint8)

    def _scale_by(self, frame, factor_u8):
        """frame * (factor/255), su tre canali."""
        factor3 = cv2.merge((factor_u8, factor_u8, factor_u8))
        return cv2.multiply(frame, factor3, scale=1.0 / 255.0)

    def _key_black(self, frame):
        luma = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self._scale_by(frame, cv2.LUT(luma, self._fade))

    def _key_green(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._GREEN_LO, self._GREEN_HI)
        # Sfuma il bordo: senza, il contorno del soggetto risulta frastagliato.
        mask = cv2.GaussianBlur(mask, (0, 0), 1.2)
        keyed = self._scale_by(frame, cv2.bitwise_not(mask))

        if self.look.green_spill:
            # Il verde riflesso sul soggetto va compresso, altrimenti resta un
            # alone verdastro sui bordi.
            b, g, r = cv2.split(keyed)
            g = cv2.min(g, cv2.max(b, r))
            keyed = cv2.merge((b, g, r))

        return keyed

    # Raggio dell'alone rispetto alla larghezza del frame, e guadagno del
    # bagliore. Tarati misurando la caduta dell'alone: con questi valori a 8
    # pixel dal soggetto vale ~60/255 e si spegne entro ~40.
    _GLOW_SIGMA_DIVISOR = 22.0
    _GLOW_GAIN = 2.0

    # Il bagliore e' per definizione a bassa frequenza, quindi la sfocatura si
    # calcola su un quarto di lato: 17 volte piu' rapida, con uno scarto medio
    # di 0,11 su 255 rispetto alla versione a piena risoluzione.
    _GLOW_DOWNSCALE = 4
    _GLOW_MIN_SIDE = 40

    def _blur_cheap(self, frame, sigma):
        h, w = frame.shape[:2]
        step = self._GLOW_DOWNSCALE
        while step > 1 and (w // step < self._GLOW_MIN_SIDE or h // step < self._GLOW_MIN_SIDE):
            step -= 1
        if step <= 1:
            return cv2.GaussianBlur(frame, (0, 0), sigma)

        small = cv2.resize(frame, (w // step, h // step), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), max(0.8, sigma / step))
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

    def _add_glow(self, frame):
        sigma = max(2.0, frame.shape[1] / self._GLOW_SIGMA_DIVISOR)
        bloom = self._blur_cheap(frame, sigma)
        bloom = cv2.convertScaleAbs(bloom, alpha=self.look.glow * self._GLOW_GAIN)
        # Fusione "screen": schiarisce solo dove c'e' gia' luce, quindi il
        # fondo nero resta nero, che e' esattamente cio' che serve al vetro.
        inv = cv2.multiply(cv2.bitwise_not(frame), cv2.bitwise_not(bloom),
                           scale=1.0 / 255.0)
        return cv2.bitwise_not(inv)

    def _key_segmentation(self, frame):
        alpha = self._segmenter.alpha(frame)
        factor = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
        return self._scale_by(frame, factor)

    def apply(self, frame):
        if self._motion is not None:
            alpha = self._motion.alpha(frame)
            frame = self._scale_by(frame, np.clip(alpha * 255.0, 0, 255).astype(np.uint8))
        elif self._segmenter is not None:
            frame = self._key_segmentation(frame)
        elif self.look.background == "black":
            frame = self._key_black(frame)
        elif self.look.background == "green":
            frame = self._key_green(frame)

        if self.look.glow > 0:
            frame = self._add_glow(frame)

        return frame


_bounds_cache = {}


def content_bounds(src, samples=24, threshold=18, margin=0.02):
    """Riquadro che racchiude il soggetto, campionando il video.

    Serve a "riempire la faccia": la maggior parte dei filmati lascia molto
    vuoto attorno al soggetto, che nella piramide diventa spazio sprecato.
    Restituisce (x, y, w, h) in pixel della sorgente, oppure None.

    Il risultato viene memorizzato: l'analisi campiona il video e costa circa
    un secondo, che altrimenti si pagherebbe sia in anteprima sia in
    conversione.
    """
    try:
        key = (os.path.abspath(src), os.path.getmtime(src), samples, threshold, margin)
    except OSError:
        key = None
    if key is not None and key in _bounds_cache:
        return _bounds_cache[key]

    result = _content_bounds_uncached(src, samples, threshold, margin)
    if key is not None:
        if len(_bounds_cache) > 64:
            _bounds_cache.clear()
        _bounds_cache[key] = result
    return result


def cached_bounds(src, samples=24, threshold=18, margin=0.02):
    """Bounds gia' calcolati, oppure None. Non analizza nulla.

    Serve all'interfaccia, che deve restare reattiva: l'analisi vera gira sul
    thread dell'anteprima.
    """
    try:
        key = (os.path.abspath(src), os.path.getmtime(src), samples, threshold, margin)
    except OSError:
        return None
    return _bounds_cache.get(key)


def _content_bounds_uncached(src, samples, threshold, margin):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        return None

    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if src_w <= 0 or src_h <= 0:
            return None

        positions = ([int(total * i / samples) for i in range(samples)]
                     if total > samples else [0])

        box = None
        for pos in positions:
            if total > samples:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue

            small = resize_to_width(frame, 240) if src_w > 240 else frame
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            found = cv2.boundingRect(mask)
            if found[2] == 0 or found[3] == 0:
                continue

            scale = src_w / float(small.shape[1])
            x, y, w, h = (int(v * scale) for v in found)
            box = (x, y, w, h) if box is None else (
                min(box[0], x), min(box[1], y),
                max(box[0] + box[2], x + w) - min(box[0], x),
                max(box[1] + box[3], y + h) - min(box[1], y),
            )
    finally:
        cap.release()

    if box is None:
        return None

    x, y, w, h = box
    pad_x, pad_y = int(w * margin), int(h * margin)
    x = max(0, x - pad_x)
    y = max(0, y - pad_y)
    w = min(src_w - x, w + 2 * pad_x)
    h = min(src_h - y, h + 2 * pad_y)

    # Un ritaglio che copre quasi tutto non vale il disturbo.
    if w * h > 0.92 * src_w * src_h:
        return None
    return (x, y, w, h)


# ----------------------------------------------------------------- sorgente

def probe(path):
    """Legge i metadati del video senza decodificarlo."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ConversionError("Impossibile aprire il video. Il formato potrebbe non essere supportato.")

    try:
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    finally:
        cap.release()

    if width <= 0 or height <= 0:
        raise ConversionError("Il file non sembra contenere un flusso video valido.")

    if not 0 < fps <= 240:
        fps = 30.0

    return {
        "frames": max(0, frames),
        "width": width,
        "height": height,
        "fps": fps,
        "duration": frames / fps if frames > 0 else 0.0,
        "size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
    }


class _FFmpegReader:
    """Decodifica e ridimensiona con ffmpeg, restituendo frame BGR grezzi.

    ffmpeg fa i due passaggi insieme, con decodifica e scaler multi-thread:
    sulla stessa sorgente rende circa 4 volte i frame al secondo di
    VideoCapture.read() seguito da cv2.resize(INTER_AREA).
    """

    def __init__(self, path, width, height, threads=0, crop=None, trim=None):
        self.width = width
        self.height = height
        self._frame_bytes = width * height * 3

        chain = []
        if trim is not None:
            start, end = trim
            chain.append(f"trim=start_frame={start}:end_frame={end}")
            chain.append("setpts=PTS-STARTPTS")
        if crop is not None:
            x, y, w, h = crop
            chain.append(f"crop={w}:{h}:{x}:{y}")
        chain.append(f"scale={width}:{height}:flags=area")

        self._process = subprocess.Popen(
            [
                FFMPEG, "-v", "error", "-nostdin",
                "-threads", str(threads),
                "-i", path,
                "-vf", ",".join(chain),
                "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=self._frame_bytes * 8,
            **_NO_WINDOW,
        )

    def __iter__(self):
        read = self._process.stdout.read
        while True:
            buf = read(self._frame_bytes)
            if buf is None or len(buf) < self._frame_bytes:
                break
            yield np.frombuffer(buf, np.uint8).reshape(self.height, self.width, 3)

    def close(self):
        process = self._process
        if process.poll() is None:
            process.kill()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        process.wait()


class _OpenCVReader:
    """Ripiego quando ffmpeg non e' installato."""

    def __init__(self, path, width, height, crop=None, trim=None):
        self.width = width
        self.height = height
        self.crop = crop
        self.trim = trim
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise ConversionError("Impossibile aprire il video sorgente.")
        if trim is not None and trim[0] > 0:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, trim[0])

    def __iter__(self):
        remaining = (self.trim[1] - self.trim[0]) if self.trim is not None else None
        while True:
            if remaining is not None:
                if remaining <= 0:
                    break
                remaining -= 1
            ok, frame = self._cap.read()
            if not ok or frame is None:
                break
            if self.crop is not None:
                x, y, w, h = self.crop
                frame = frame[y:y + h, x:x + w]
            yield cv2.resize(frame, (self.width, self.height),
                             interpolation=cv2.INTER_AREA)

    def close(self):
        self._cap.release()


def _open_reader(path, width, height, use_threads, crop=None, trim=None):
    if has_ffmpeg():
        return _FFmpegReader(path, width, height,
                             threads=0 if use_threads else 1, crop=crop, trim=trim)
    return _OpenCVReader(path, width, height, crop=crop, trim=trim)


# ---------------------------------------------------------------- anteprima

def preview_frame(src, base_width=300, position=0.1, look=None):
    """Compone un singolo frame, per mostrare l'anteprima del risultato.

    `position` e' la posizione relativa nel video (0.1 = 10%): i primi frame
    sono spesso neri e non direbbero granche'.
    """
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise ConversionError("Impossibile aprire il video sorgente.")

    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > 1:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * position))

        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok or frame is None:
            raise ConversionError("Nessun frame leggibile nel video sorgente.")
    finally:
        cap.release()

    look = look or Look()
    if look.autofit:
        crop = content_bounds(src)
        if crop is not None:
            x, y, w, h = crop
            frame = frame[y:y + h, x:x + w]

    small = resize_to_width(frame, base_width)
    if look.touches_pixels:
        small = _LookProcessor(
            look, source=src, size=(small.shape[1], small.shape[0])).apply(small)

    return compose_frame(small, new_canvas(small))


# --------------------------------------------------------------------- loop

# Lato dei descrittori usati per confrontare i frame. Bastano poche decine di
# pixel: serve la somiglianza d'insieme, non il dettaglio.
_LOOP_DESC_W, _LOOP_DESC_H = 32, 18

# Oltre questo numero di candidati la matrice delle distanze diventa pesante,
# quindi si cerca a passo piu' largo e si rifinisce attorno al risultato.
_LOOP_MAX_CANDIDATES = 4000


class LoopResult:
    """Punto di taglio trovato: il video va riprodotto da `start` a `end`."""

    def __init__(self, start, end, score, baseline, fps):
        self.start = start
        self.end = end
        self.score = score              # differenza media per pixel, 0..255
        self.baseline = baseline        # stessa misura sul video intero
        self.fps = fps

    @property
    def frames(self):
        return self.end - self.start

    @property
    def duration(self):
        return self.frames / self.fps if self.fps else 0.0

    @property
    def improvement(self):
        """Quante volte lo stacco e' meno visibile rispetto al video intero."""
        if self.score <= 0.01:
            return float("inf")
        return self.baseline / self.score

    def __repr__(self):
        return (f"LoopResult(start={self.start}, end={self.end}, "
                f"frames={self.frames}, score={self.score:.2f}, "
                f"baseline={self.baseline:.2f})")


def _loop_descriptors(src):
    """Miniature in scala di grigi di tutti i frame, come vettori."""
    size = _LOOP_DESC_W * _LOOP_DESC_H

    if has_ffmpeg():
        process = subprocess.Popen(
            [
                FFMPEG, "-v", "error", "-nostdin", "-threads", "0", "-i", src,
                "-vf", f"scale={_LOOP_DESC_W}:{_LOOP_DESC_H}:flags=area",
                "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=size * 512, **_NO_WINDOW,
        )
        frames = []
        try:
            while True:
                buf = process.stdout.read(size)
                if buf is None or len(buf) < size:
                    break
                frames.append(np.frombuffer(buf, np.uint8))
        finally:
            process.stdout.close()
            process.wait()
        return np.asarray(frames, np.float32)

    cap = cv2.VideoCapture(src)
    frames = []
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            small = cv2.resize(frame, (_LOOP_DESC_W, _LOOP_DESC_H),
                               interpolation=cv2.INTER_AREA)
            frames.append(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).ravel())
    finally:
        cap.release()
    return np.asarray(frames, np.float32)


def _pair_costs(desc, index):
    """Costo di ogni coppia (inizio, fine) fra i frame elencati in `index`.

    Il costo confronta due frame consecutivi e non uno solo: due pose identiche
    percorse in direzioni opposte hanno la stessa immagine ma non si
    raccordano, e la finestra a due frame le distingue.
    """
    a = desc[index]
    b = desc[np.minimum(index + 1, len(desc) - 1)]

    def squared(m):
        sq = (m * m).sum(1)
        return np.maximum(sq[:, None] + sq[None, :] - 2.0 * (m @ m.T), 0.0)

    return squared(a) + squared(b)


def _rms(cost):
    """Da distanza quadratica sommata a differenza media per pixel."""
    return float(np.sqrt(max(cost, 0.0) / (2.0 * _LOOP_DESC_W * _LOOP_DESC_H)))


_loop_cache = {}


def cached_loop(src, min_ratio=0.35):
    """Loop gia' calcolato, oppure None. Non analizza nulla."""
    try:
        key = (os.path.abspath(src), os.path.getmtime(src), min_ratio)
    except OSError:
        return None
    return _loop_cache.get(key)


def find_loop(src, min_ratio=0.35, fps=None):
    """Cerca il punto di taglio che rende la ripetizione meno visibile.

    Restituisce un LoopResult, oppure None se il video e' troppo corto.
    Il ciclo comprende i frame da `start` incluso a `end` escluso: alla
    ripetizione si passa dal frame end-1 al frame start, quindi si cerca la
    coppia in cui il frame `end` somiglia di piu' al frame `start`.
    """
    try:
        key = (os.path.abspath(src), os.path.getmtime(src), min_ratio)
    except OSError:
        key = None
    if key is not None and key in _loop_cache:
        return _loop_cache[key]

    result = _find_loop_uncached(src, min_ratio, fps)
    if key is not None:
        if len(_loop_cache) > 64:
            _loop_cache.clear()
        _loop_cache[key] = result
    return result


def _find_loop_uncached(src, min_ratio, fps):
    desc = _loop_descriptors(src)
    total = len(desc)
    if total < 30:
        return None

    if fps is None:
        fps = probe(src)["fps"]

    min_len = max(int(total * min_ratio), int(fps * 2), 10)
    if min_len >= total - 1:
        return None

    # Confronto del video preso per intero, come termine di paragone.
    baseline = _rms(_pair_costs(desc, np.array([0, total - 1]))[0, 1])

    stride = max(1, -(-total // _LOOP_MAX_CANDIDATES))
    index = np.arange(0, total, stride)
    start, end, score = _best_pair(desc, index, min_len)

    if stride > 1:
        # Rifinitura a passo pieno attorno alla coppia trovata.
        lo_s, hi_s = max(0, start - stride), min(total, start + stride + 1)
        lo_e, hi_e = max(0, end - stride), min(total, end + stride + 1)
        index = np.unique(np.concatenate([np.arange(lo_s, hi_s),
                                          np.arange(lo_e, hi_e)]))
        start, end, score = _best_pair(desc, index, min_len)

    if start is None:
        return None
    return LoopResult(int(start), int(end), _rms(score), baseline, fps)


def _best_pair(desc, index, min_len):
    cost = _pair_costs(desc, index)

    span = index[None, :] - index[:, None]
    cost = np.where(span >= min_len, cost, np.inf)
    if not np.isfinite(cost).any():
        return None, None, None

    # A parita' pratica di raccordo si preferisce il ciclo piu' lungo: una
    # tolleranza sul minimo evita di scartare un loop molto piu' ampio per una
    # differenza impercettibile.
    best = cost.min()
    tolerance = best + max(best * 0.05, 1.0)
    acceptable = np.argwhere(cost <= tolerance)
    lengths = span[acceptable[:, 0], acceptable[:, 1]]
    chosen = acceptable[int(np.argmax(lengths))]

    i, j = int(chosen[0]), int(chosen[1])
    return index[i], index[j], float(cost[i, j])


# -------------------------------------------------------------- conversione

def _fourcc_for(path):
    """Sceglie il codec in base all'estensione del file di destinazione."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".avi":
        return cv2.VideoWriter_fourcc(*"XVID")
    return cv2.VideoWriter_fourcc(*"mp4v")


def convert(src, dst, base_width=300, use_threads=True, look=None, loop=False,
            on_progress=None, on_preview=None, should_cancel=None,
            preview_every=12):
    """Converte `src` nell'ologramma `dst`.

    on_progress(done, total, phase)  -- avanzamento; total puo' essere 0 se il
                                        numero di frame non e' noto.
    on_preview(frame_bgr)            -- copia di un frame composto, ogni tanto,
                                        per l'anteprima dal vivo.
    should_cancel()                  -- se restituisce True la conversione si
                                        interrompe e il file parziale viene
                                        rimosso.
    look                             -- trattamento dei frame (vedi Look).
    loop                             -- taglia il video nel punto in cui la
                                        ripetizione si nota di meno.
    """

    look = look or Look()

    info = probe(src)
    total = info["frames"]
    fps = info["fps"]

    trim = None
    if loop:
        found = find_loop(src, fps=fps)
        if found is not None:
            trim = (found.start, found.end)
            total = found.frames

    # Il ritaglio va deciso prima: cambia le proporzioni, quindi la
    # dimensione del canvas. Lo esegue ffmpeg nella stessa passata di
    # ridimensionamento, cosi' non costa nulla.
    crop = content_bounds(src) if look.autofit else None
    source_w = crop[2] if crop else info["width"]
    source_h = crop[3] if crop else info["height"]

    # Larghezza pari: cosi' il lato del canvas resta pari e gli encoder
    # H.264 accettano il risultato.
    width = max(2, int(base_width) & ~1)
    height = scaled_height(source_w, source_h, width)
    side = layout(height, width)

    processor = (_LookProcessor(look, source=src, size=(width, height))
                 if look.touches_pixels else None)

    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)

    writer = cv2.VideoWriter(dst, _fourcc_for(dst), fps, (side, side))
    if not writer.isOpened():
        raise ConversionError(
            "Impossibile creare il file di output. "
            "Verifica il percorso e che il file non sia gia' aperto."
        )

    reader = _open_reader(src, width, height, use_threads, crop=crop, trim=trim)

    # Canvas che ruotano tra chi compone e chi scrive: senza il pool servirebbe
    # una copia da ~1,2 MB per frame solo per passare il buffer al writer.
    pending = queue.Queue(maxsize=_BUFFER_COUNT)
    recycled = queue.Queue()
    for _ in range(_BUFFER_COUNT):
        recycled.put(np.zeros((side, side, 3), np.uint8))

    failure = {}

    def write_loop():
        while True:
            canvas = pending.get()
            if canvas is None:
                break
            try:
                writer.write(canvas)
            except Exception as exc:          # pragma: no cover - difensivo
                failure["error"] = exc
                break
            finally:
                recycled.put(canvas)

    writer_thread = threading.Thread(target=write_loop, daemon=True)
    writer_thread.start()

    written = 0
    cancelled = False

    try:
        for frame in reader:
            if should_cancel is not None and should_cancel():
                cancelled = True
                break
            if "error" in failure:
                break

            if processor is not None:
                frame = processor.apply(frame)

            canvas = _take_buffer(recycled, failure, writer_thread)
            if canvas is None:
                break

            pending.put(compose_frame(frame, canvas))
            written += 1

            if on_progress is not None:
                on_progress(written, total, "Creazione ologramma")

            if on_preview is not None and (written == 1 or written % preview_every == 0):
                on_preview(canvas.copy())
    finally:
        pending.put(None)
        writer_thread.join()
        writer.release()
        reader.close()

    if "error" in failure:
        _remove_quietly(dst)
        raise ConversionError(f"Errore durante la scrittura del video: {failure['error']}")

    if cancelled:
        _remove_quietly(dst)
        raise ConversionCancelled()

    if written == 0:
        _remove_quietly(dst)
        raise ConversionError("Nessun frame leggibile nel video sorgente.")

    if on_progress is not None:
        on_progress(written, written, "Completato")

    return {
        "frames": written,
        "fps": fps,
        "side": side,
        "crop": crop,
        "trim": trim,
        "output": dst,
        "size_bytes": os.path.getsize(dst) if os.path.exists(dst) else 0,
    }


def _take_buffer(recycled, failure, writer_thread):
    """Preleva un canvas libero senza rischiare di bloccarsi per sempre.

    Se il thread di scrittura si e' fermato nessuno rimettera' piu' buffer in
    circolo, quindi l'attesa va interrotta.
    """
    while True:
        try:
            return recycled.get(timeout=0.5)
        except queue.Empty:
            if "error" in failure or not writer_thread.is_alive():
                return None


# -------------------------------------------------------------- modelli 3D

def compose_views(views, canvas):
    """Come compose_frame, ma con una ripresa diversa per ogni faccia.

    `views` e' il dizionario restituito da TurntableRenderer.render_views():
    immagini quadrate, una per direzione. E' questa la differenza fra un video
    ripetuto quattro volte e un vero ologramma, in cui girando attorno alla
    piramide si vede l'oggetto da un altro lato.
    """
    n = views["up"].shape[0]

    canvas[0:n, n:n + n] = views["up"]
    canvas[n:n + n, 0:n] = cv2.rotate(views["left"], _CCW)
    canvas[n + n:n + n + n, n:n + n] = cv2.rotate(views["down"], _R180)
    canvas[n:n + n, n + n:n + n + n] = cv2.rotate(views["right"], _CW)

    return canvas


def model_info(path):
    """Metadati del modello, senza aprire un contesto grafico."""
    import trimesh

    loaded = trimesh.load(path, force="mesh", process=False)
    if hasattr(loaded, "geometry"):
        meshes = [g for g in loaded.geometry.values() if hasattr(g, "faces")]
        loaded = trimesh.util.concatenate(meshes) if meshes else loaded

    faces = len(getattr(loaded, "faces", ()))
    if faces == 0:
        raise ConversionError("Il file non contiene triangoli.")

    return {
        "triangles": faces,
        "vertices": len(loaded.vertices),
        "size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
    }


def preview_model(path, base_width=300, turn=25.0, look=None):
    """Un fotogramma composto dal modello, per l'anteprima."""
    import render3d

    look = look or Look()
    processor = _LookProcessor(look) if look.glow > 0 else None

    renderer = render3d.TurntableRenderer(path, size=base_width)
    try:
        views = renderer.render_views(turn)
    finally:
        renderer.close()

    if processor is not None:
        views = {k: processor._add_glow(v) for k, v in views.items()}

    side = 3 * base_width
    return compose_views(views, np.zeros((side, side, 3), np.uint8))


def convert_model(path, dst, base_width=300, seconds=8.0, fps=30.0, turns=1.0,
                  elevation=None, look=None,
                  on_progress=None, on_preview=None, should_cancel=None,
                  preview_every=8):
    """Genera l'ologramma di un modello 3D che ruota su se stesso.

    La GPU viene impegnata solo per la durata di questa chiamata: il contesto
    grafico nasce qui e viene chiuso prima di uscire, anche in caso di errore.
    """
    import render3d

    look = look or Look()
    processor = _LookProcessor(look) if look.glow > 0 else None

    width = max(2, int(base_width) & ~1)
    side = 3 * width
    total = max(1, int(round(seconds * fps)))

    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)

    writer = cv2.VideoWriter(dst, _fourcc_for(dst), fps, (side, side))
    if not writer.isOpened():
        raise ConversionError("Impossibile creare il file di output.")

    renderer = None
    canvas = np.zeros((side, side, 3), np.uint8)
    written = 0
    cancelled = False

    try:
        renderer = render3d.TurntableRenderer(path, size=width)
        elev = render3d.DEFAULT_ELEVATION if elevation is None else float(elevation)

        for index in range(total):
            if should_cancel is not None and should_cancel():
                cancelled = True
                break

            views = renderer.render_views(360.0 * turns * index / total, elev)
            if processor is not None:
                views = {k: processor._add_glow(v) for k, v in views.items()}

            compose_views(views, canvas)
            writer.write(canvas)
            written += 1

            if on_progress is not None:
                on_progress(written, total, "Rendering del modello")
            if on_preview is not None and (written == 1 or written % preview_every == 0):
                on_preview(canvas.copy())
    finally:
        if renderer is not None:
            renderer.close()
        writer.release()

    if cancelled:
        _remove_quietly(dst)
        raise ConversionCancelled()

    if on_progress is not None:
        on_progress(written, written, "Completato")

    return {
        "frames": written,
        "fps": fps,
        "side": side,
        "crop": None,
        "trim": None,
        "output": dst,
        "size_bytes": os.path.getsize(dst) if os.path.exists(dst) else 0,
    }


def _remove_quietly(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
