# py-hologram

A Python application for creating hologram videos from regular video files. This project uses computer vision techniques to transform standard videos into holographic displays that can be viewed on pyramid-shaped hologram displays.

## Features

- **Video to Hologram Conversion**: Transform any video file into a hologram format
- **Modern GUI**: Drag & drop, live preview, light and dark themes
- **Background Removal**: motion differencing (fast, no model) or AI cut-out (U^2-Net), plus luma and chroma keying
- **3D Models**: load a .glb/.obj and get real parallax — each face shows a different side
- **Hologram Look**: bloom glow and auto-fill of the pyramid face
- **Perfect Loop**: finds the cut where the repeat is least visible, for continuous displays
- **Batch**: drop several clips and convert them all with the same settings
- **Fast**: ffmpeg-backed pipeline, ~5x the throughput of the original implementation
- **Constant Memory**: Streaming conversion, so video length does not drive RAM usage
- **Real-time Progress**: Percentage, remaining time and a live preview, cancellable at any point
- **Optimized Performance**: Numba JIT compilation, optional multi-core processing

## How It Works

The application creates hologram videos by:
1. Taking each frame from the input video
2. Resizing frames to a specified width (default: 300px)
3. Creating a 4-sided hologram layout by placing the frame in four orientations:
   - **Up**: Normal orientation
   - **Left**: Rotated 90° counter-clockwise
   - **Down**: Rotated 180° (upside down)
   - **Right**: Rotated 90° clockwise
4. Combining all orientations into a single hologram frame
5. Outputting the final hologram video

## Project Structure

```
py-hologram/
├── main/
│   ├── engine.py           # Conversion engine (streaming, Numba-accelerated)
│   ├── app.py              # Modern GUI - the application entry point
│   ├── main.py             # Legacy engine (kept for the old Kivy UI)
│   ├── test.py             # Legacy Kivy UI
│   ├── UI.py               # Legacy, unused
│   └── *.kv                # Legacy Kivy layouts
├── holograms/              # Generated hologram videos
├── phototest/              # Sample media
└── requirements.txt
```

## Dependencies

- **OpenCV (cv2)**: frame composition and video encoding
- **NumPy**: array operations
- **Pillow**: preview rendering
- **CustomTkinter**: the graphical interface
- **tkinterdnd2**: drag & drop support (optional)
- **ffmpeg** (external binary, optional but recommended): decoding and scaling.
  Without it the app falls back to OpenCV and runs about 4x slower.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dima-sw/py-hologram.git
   cd py-hologram
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS / Linux:
   source .venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install ffmpeg and make sure it is on your `PATH` (strongly recommended):
   ```bash
   winget install Gyan.FFmpeg
   ```

## Usage

Launch the application:

```bash
python main/app.py
```

Then:

1. Drag one or more videos onto the window, or click to pick them. A preview
   of the resulting hologram appears straight away.
2. Pick a quality preset and the look options you want.
3. Click **Crea ologramma**. Progress, remaining time and a live preview are
   shown while the video is written; the conversion can be cancelled at any
   time.
4. The result lands in `holograms/` as an MP4, named after the source video.
   Existing files are never overwritten.

With several videos queued the progress line reads `File 2 di 5`, each file
counts equally toward the overall bar, and cancelling stops the whole queue
without leaving partial files behind.

### Programmatic usage

```python
from main import engine

engine.convert(
    "phototest/star.mp4",
    "holograms/star_hologram.mp4",
    base_width=300,
    use_threads=True,
    on_progress=lambda done, total, phase: print(f"{done}/{total}"),
)
```

`engine.probe(path)` returns the source metadata, and
`engine.preview_frame(path)` composes a single frame without writing a file.

### Legacy Kivy interface

The original interface is still in the repository and can be started with
`python main/test.py` (requires `kivy`). It uses `main/main.py`, which loads
the whole video into memory.

## Configuration Options

### Quality

Controls the width each of the four views is rendered at. The resulting
canvas size is shown live in the app.

| Preset  | Frame width | Output size (16:9 source) |
|---------|-------------|---------------------------|
| Bassa   | 200 px      | ~426 x 426                |
| Media   | 300 px      | ~638 x 638                |
| Alta    | 480 px      | ~1020 x 1020              |
| Massima | 640 px      | ~1360 x 1360              |

Decoding always uses every CPU core; there is no reason to ask for less.

### Look

| Option | What it does |
|--------|--------------|
| **Togli sfondo: movimento** | Reconstructs the background as a per-pixel temporal median and subtracts it. Needs a locked-off camera and a subject that moves. ~300 fps, no model file. Anything that does not move — statues, furniture — becomes background by definition. |
| **Togli sfondo: persona** | Cuts the subject out with `u2net_human_seg`. This is the one to use for a person filmed anywhere. ~1.8 fps. |
| **Togli sfondo: oggetto** | Same, with the general-purpose `u2netp`. Roughly twice as fast, and works on non-human subjects, but it keeps every salient object in frame, not just the one you meant. |
| **Solo fondo scuro** | Fades *already dark* pixels to pure black with a soft knee. Cheap and instant, but it does nothing to a real background — use the AI modes for that. |
| **Green screen** | Keys out a green background in HSV, feathers the edge, and suppresses green spill on the subject. |
| **Bagliore** | Screen-blended bloom around bright areas. `Lieve` (0.3) or `Intenso` (0.5) — above ~0.6 the highlights blow out to white. |
| **Riempi la faccia** | Samples the video, finds the box that contains the subject, and crops to it so the subject fills the pyramid face instead of floating in empty space. The crop is handed to ffmpeg's filter chain, so it costs nothing to apply. |
| **Loop perfetto** | Trims the video to the cut where the repeat is least visible. See below. |

Note that **Riempi la faccia** changes the aspect ratio, and therefore the
canvas size: a portrait subject produces a taller canvas. The app shows the
resulting size before you start.

## Output

Hologram videos are written to `holograms/` as MP4 files at the source frame
rate. Existing files are never overwritten: a numeric suffix is added instead.
Play them full screen on a display with a hologram pyramid on top.

## Perfect Loop

Content on a pyramid usually runs unattended on repeat, and the jump at the
wrap is the most noticeable defect there is. `Loop perfetto` picks the cut that
minimises it.

Every frame is reduced to a 32x18 greyscale descriptor (ffmpeg does this at
over 1000 fps, so a minute of video is analysed in ~1.4s). The loop plays
frames `[start, end)`, so the wrap goes from `end-1` back to `start`, and the
cost to minimise is the distance between frame `start` and frame `end`.

The comparison uses a **two-frame window** rather than a single frame: two
identical poses travelled in opposite directions look the same in one frame but
do not join up, and the second frame separates them. Among cuts within 5% of
the best score the longest one wins.

Measured as mean per-pixel difference at the wrap (0-255):

| Source | Whole video | Best cut found | Loop kept |
|--------|-------------|----------------|-----------|
| star.mp4 | 6.64 | 0.33 (20x better) | 45.0s of 62.6s |
| spong.mp4 | 30.36 | 0.15 (198x better) | 40.0s of 60.2s |

## Background Removal

Three approaches, and which one to use depends on the shot.

### Motion differencing — `Togli sfondo: movimento`

The background is reconstructed as the **per-pixel temporal median** of 41
frames sampled across the video. The median, not the mean: a subject crossing
the frame leaves no trail, as long as it does not linger on the same spot for
more than half the clip. Each frame is then compared against that plate in Lab
space.

Details that matter:

- **Shadow suppression**: a pixel that is darker but the same colour is almost
  always a shadow, so a drop in lightness is weighted at 0.3 against a rise.
- **Hysteresis**, as in Canny: only regions above the low threshold that
  contain a pixel above the high threshold are kept. A single threshold either
  crumbles the subject or swallows noise.
- Interior holes are filled, and blobs far smaller than the subject are
  dropped — compression noise on hard background edges trips the threshold now
  and then.

Measured against a clip with a known mask: **IoU 0.781 at 3.6 ms/frame**,
against 0.879 at 218 ms for the AI. So roughly 60x faster for slightly looser
edges — and it removes static clutter that a saliency model would keep.

**It is checked automatically.** Before running, the app measures camera
movement by phase correlation and how much of the frame the mask claims. If
the camera moves more than ~2 px, or the plate turns out to contain the
subject, it says so in red instead of producing rubbish.

### AI cut-out — `persona` / `oggetto`

Requires the ONNX models — see [models/README.md](models/README.md). Without
them the app still runs and says what is missing.

U^2-Net through `onnxruntime` on CPU, run on the already-downscaled frame (the
network resizes to 320x320 internally, so a larger source buys nothing). Four
inference threads measured fastest; six are slower, because the threads
contend.

| Model | Size | Throughput |
|-------|------|-----------|
| `u2net_human_seg` | 176 MB | 1.8 fps |
| `u2netp` | 4.6 MB | 4.9 fps |

By far the slowest stage in the project — a 4.5s clip takes ~75s. Use it when
the camera moves, which is where differencing cannot help.

Both methods feather the mask and blend it with the previous frame (70/30): a
mask computed independently per frame flickers along the edges.

## 3D Models

Load a `.glb`, `.gltf`, `.obj`, `.stl` or `.ply` and the app renders a turntable
straight to hologram: **four cameras 90 degrees apart**, so each pyramid face
shows a genuinely different side of the object. Walking around the pyramid then
shows real parallax, which repeating one video four times can never do.

Defaults to one full turn in 8 seconds at 30 fps. Rendering runs at over 1000
frames per second on a mid-range GPU, so the render is never the bottleneck.

**The GPU is touched only while rendering.** `moderngl` and `trimesh` are
imported inside the renderer, not at module load, and the OpenGL context is
created in `TurntableRenderer.__init__` and destroyed in `close()`, including on
error. Opening the app, or converting ordinary video, never creates a graphics
context at all.

Shading is flat (per-face normals) with two camera-space lights and a rim term.
Textures are not read yet; vertex colours and a material's base colour are.

## Technical Details

### Pipeline

```
ffmpeg (decode + scale, multi-threaded)
    -> composition with cv2.rotate (SIMD)
        -> encoding on a dedicated thread
```

Frames are read, composed and written one at a time, so RAM usage does not
grow with the length of the video.

### Why this shape

Profiling the naive version showed the cost was not where you would expect:

| Stage             | Share of runtime |
|-------------------|------------------|
| Resize            | 45%              |
| Decode            | 37%              |
| Encode            | 11%              |
| Frame composition | 8%               |

So the optimisations target decoding and scaling, not the composition kernel:

- **ffmpeg does decode and scale together**, multi-threaded, in one pass:
  ~413 fps against ~91 fps for `VideoCapture.read()` plus
  `cv2.resize(INTER_AREA)`. `INTER_AREA` alone is 21x slower than
  `INTER_LINEAR` on a 6x downscale, and it dominated the old pipeline.
- **`cv2.rotate` replaced the Numba kernel**: 1.97x faster, and it removes the
  ~5s JIT compilation on first launch. Numba is no longer a dependency.
- **The encoder runs on its own thread**, with a pool of four canvases
  rotating between composition and writing, which avoids a 1.2 MB copy per
  frame.
- **The canvas side is even**, so H.264 encoders in yuv420p accept it. The
  previous layout added an arbitrary `+1` that made it odd and asymmetric.

Measured end to end on `phototest/star.mp4` (1564 frames, 1920x1080, 6 cores):
**21s -> 4.0s, about 5x**. The OpenCV fallback is ~4.9x slower than the ffmpeg
path but still beats the original implementation.

The look options are close to free, because the pipeline is bound by decoding
and the pixel work hides behind it:

| Look | Time | Throughput |
|------|------|-----------|
| None | 4.2s | 370 fps |
| Background keying | 3.8s | 417 fps |
| Keying + glow | 4.5s | 351 fps |
| + fill the face | 6.1s | 258 fps |

The bloom is blurred at **quarter resolution** and scaled back up: 17x faster
than the full-resolution Gaussian, with a mean deviation of 0.11/255, which is
not visible. At full resolution the glow alone cost 3-4x the whole pipeline.

The cost of *fill the face* is not the crop, which is free — it is the larger
output canvas that follows from a subject-shaped aspect ratio.

GPU encoding via NVENC was measured and is *slower* here: the frames are small
(638x638), so the transfer and setup cost outweighs the encoding.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the terms specified in the LICENSE file.
