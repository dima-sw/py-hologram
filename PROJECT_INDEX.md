# py-hologram Project Index

## Project Overview
**py-hologram** is a Python application that converts regular video files into hologram videos suitable for pyramid-shaped hologram displays. The application uses computer vision techniques and multi-threading for efficient processing.

## Core Functionality
- **Video Processing**: Converts input videos to hologram format
- **4-Sided Layout**: Creates hologram frames with four orientations (up, left, down, right)
- **Performance Optimization**: Uses Numba JIT compilation and optional multi-threading
- **GUI Interface**: Kivy-based user interface for easy operation

## Project Structure

### Main Application (`main/`)
- **`main.py`** - Core hologram processing logic
  - `Hologram` class: Manages hologram model creation and properties
  - `frameToHol()`: Numba-optimized function for frame-to-hologram conversion
  - `videoToNumpy()`: Loads video files into numpy arrays
  - `makeVideo()`: Main processing function
  - `th` class: Threading wrapper for background processing

- **`test.py`** - Main application entry point
  - `Root` class: Main UI controller
  - `LoadDialog` class: File selection dialog
  - `Editor` class: Kivy application class

- **`UI.py`** - Additional UI components (legacy/unused)
  - Contains older UI implementations

- **UI Layout Files**:
  - **`editor.kv`** - Main application UI layout
  - **`fileChooser.kv`** - File chooser dialog layout (empty)
  - **`spin.kv`** - Additional UI components (empty)

### Output Directory (`holograms/`)
Contains generated hologram videos:
- `output_video.avi`
- `rar.avi` 
- `star.avi`

### Test Media (`phototest/`)
Contains sample media files for testing:
- `spong.mp4` - Test video
- `star.mp4` - Test video
- `test.jpg` - Test image (used as logo in UI)

### Virtual Environment (`venv/`)
Complete Python virtual environment with all dependencies installed.

## Dependencies

### Core Libraries
- **OpenCV (cv2)** - Computer vision and video processing
- **NumPy** - Numerical computing and array operations
- **Numba** - JIT compilation for performance optimization
- **Kivy** - Cross-platform GUI framework
- **Multiprocessing** - Multi-threading support

### Additional Dependencies (from venv analysis)
- **PIL/Pillow** - Image processing
- **Matplotlib** - Plotting and visualization
- **Django** - Web framework (likely unused)
- **Requests** - HTTP library
- **PyWin32** - Windows-specific functionality

## Key Classes and Functions

### `Hologram` Class
```python
class Hologram():
    def __init__(self)
    def createHologramModel(self, img)
    def getHologram(self)
    def getImgProp(self)
    def reset(self)
```

### Core Processing Functions
- `frameToHol(img, hologram, img_rows, img_cols, rgb)` - Converts single frame to hologram format
- `videoToNumpy(path, text)` - Loads video into numpy array with progress tracking
- `makeVideo(videoPath, text, basewidth=300, maxQuality=False, threading=False)` - Main processing function
- `createMP4(holograms, text)` - Saves processed hologram frames to video file

### UI Components
- `Root` - Main application window controller
- `LoadDialog` - File selection popup
- `Editor` - Kivy application class

## Configuration Options

### Processing Parameters
- **`basewidth`**: Frame width for processing (default: 300px)
- **`threading`**: Enable/disable multi-threading
- **`maxQuality`**: Quality setting (currently not fully implemented)

### Output Settings
- **Output Format**: AVI video files
- **Frame Rate**: 30 FPS
- **Codec**: DIVX

## Usage Patterns

### GUI Application
1. Run `python main/test.py`
2. Select input video file
3. Choose threading option
4. Click "Generate Hologram Video"
5. Monitor progress in real-time

### Programmatic Usage
```python
from main import makeVideo
makeVideo("path/to/video.mp4", text_widget, basewidth=300, threading=True)
```

## Technical Implementation Details

### Hologram Layout Algorithm
The application creates a 4-sided hologram by placing each frame in four orientations:
1. **Up**: Normal orientation (0°)
2. **Left**: Rotated 90° counter-clockwise
3. **Down**: Rotated 180° (upside down)
4. **Right**: Rotated 90° clockwise

### Performance Optimizations
- **Numba JIT Compilation**: `@njit` decorator on `frameToHol()` function
- **Parallel Processing**: Uses `prange` for parallel loops
- **Multi-threading**: Optional CPU core utilization
- **Memory Efficiency**: Frame-by-frame processing

### File I/O
- **Input**: Supports various video formats via OpenCV
- **Output**: AVI format with DIVX codec
- **Progress Tracking**: Real-time progress updates via text widgets

## Development Status
- **Active Development**: Yes
- **GUI**: Functional Kivy interface
- **Core Processing**: Complete and optimized
- **Documentation**: README.md present
- **Dependencies**: All installed in venv

## Known Issues/Limitations
- Hard-coded file paths in UI (e.g., logo image path)
- `maxQuality` parameter not fully implemented
- Some UI files (`fileChooser.kv`, `spin.kv`) are empty
- Legacy UI code in `UI.py` appears unused

## File Dependencies Map
```
main/test.py (entry point)
├── main/main.py (core processing)
├── main/editor.kv (UI layout)
└── main/fileChooser.kv (file dialog)

main/main.py
├── OpenCV (cv2)
├── NumPy
├── Numba
└── Multiprocessing

main/test.py
├── Kivy framework
└── main.main (th class)
```

## Installation Requirements
1. Python 3.7+ (based on venv analysis)
2. Virtual environment activation
3. Dependencies: `opencv-python numpy numba kivy`
4. Windows-specific: PyWin32 (for Windows builds)

## Project Health
- **Code Quality**: Good structure with clear separation of concerns
- **Performance**: Well-optimized with Numba JIT compilation
- **Documentation**: Comprehensive README
- **Testing**: Sample media files provided
- **Maintainability**: Clean code structure, some hard-coded paths need attention
