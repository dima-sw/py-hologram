# py-hologram

A Python application for creating hologram videos from regular video files. This project uses computer vision techniques to transform standard videos into holographic displays that can be viewed on pyramid-shaped hologram displays.

## Features

- **Video to Hologram Conversion**: Transform any video file into a hologram format
- **Multi-threading Support**: Optional multi-threading for faster processing
- **GUI Interface**: User-friendly Kivy-based graphical interface
- **Real-time Progress Tracking**: Visual progress indicators during processing
- **Optimized Performance**: Uses Numba JIT compilation for high-performance image processing

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
├── main/                    # Main application code
│   ├── main.py             # Core hologram processing logic
│   ├── UI.py               # User interface implementation
│   ├── test.py             # Main application entry point
│   ├── editor.kv           # Kivy UI layout file
│   ├── fileChooser.kv      # File chooser dialog layout
│   └── spin.kv             # Additional UI components
├── holograms/              # Output directory for generated hologram videos
│   ├── output_video.avi
│   ├── rar.avi
│   └── star.avi
├── phototest/              # Test media files
│   ├── spong.mp4
│   ├── star.mp4
│   └── test.jpg
└── venv/                   # Virtual environment
```

## Dependencies

The project requires the following Python packages:

- **OpenCV (cv2)**: Computer vision and video processing
- **NumPy**: Numerical computing and array operations
- **Numba**: JIT compilation for performance optimization
- **Kivy**: Cross-platform GUI framework
- **Multiprocessing**: Multi-threading support

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd py-hologram
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install opencv-python numpy numba kivy
   ```

## Usage

### GUI Application

1. Run the main application:
   ```bash
   python main/test.py
   ```

2. Use the interface to:
   - Select an input video file
   - Choose whether to use multi-threading (recommended for faster processing)
   - Click "Generate Hologram Video" to start processing
   - Monitor progress in real-time

### Programmatic Usage

You can also use the hologram processing functions directly:

```python
from main import makeVideo

# Process a video file
makeVideo("path/to/your/video.mp4", text_widget, basewidth=300, threading=True)
```

## Configuration Options

- **basewidth**: Controls the width of processed frames (default: 300px)
- **threading**: Enable/disable multi-threading for faster processing
- **maxQuality**: Quality setting for output (currently not fully implemented)

## Output

Generated hologram videos are saved in the `holograms/` directory as AVI files. These videos can be played on hologram pyramid displays or viewed on regular screens to see the holographic effect.

## Technical Details

- **Performance Optimization**: Uses Numba's `@njit` decorator for JIT compilation
- **Parallel Processing**: Supports multi-threading for faster frame processing
- **Memory Efficient**: Processes videos frame by frame to minimize memory usage
- **Cross-platform**: Works on Windows, macOS, and Linux

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the terms specified in the LICENSE file.
