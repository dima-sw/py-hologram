# Modelli di segmentazione

Servono solo per "Togli sfondo". Non sono nel repository perché pesano troppo:
scaricali qui dentro.

| File | Dimensione | Uso |
|------|-----------|-----|
| `u2net_human_seg.onnx` | 176 MB | Persone. Il migliore quando il soggetto è qualcuno. |
| `u2netp.onnx` | 4,6 MB | Soggetto generico. Circa il doppio più veloce. |

```bash
curl -L -o models/u2net_human_seg.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx
curl -L -o models/u2netp.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx
```

L'inferenza gira con `onnxruntime` su CPU. L'app funziona anche senza questi
file: le altre modalità di sfondo restano disponibili e segnala cosa manca.
