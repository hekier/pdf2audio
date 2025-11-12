# PDF to Audio Converter

A Python command-line application that converts PDF documents to natural-sounding audiobooks in M4B format using local text-to-speech technology.

## Features

- Extract text from PDF documents with high accuracy
- Convert to natural-sounding speech using Piper TTS
- Output in M4B audiobook format with chapter markers and metadata
- Fully local processing (no cloud services required)
- Test random pages before full conversion
- Multiple PDF layout handling with fallback strategies
- Progress indicators and dependency validation

## Requirements

- Python 3.8 or higher
- ffmpeg (system binary)
- 500MB - 1GB RAM depending on PDF size

## Installation

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Windows
Download and install ffmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

### 2. Set Up Python Environment

```bash
# Clone or navigate to the project directory
cd pdf2audio

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Download Voice Models

Piper TTS requires voice models. The project includes both English and Danish voices:

**English Voice (en_US-lessac-medium):**
```bash
cd models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
cd ..
```

**Danish Voice (da_DK-talesyntese-medium):**
```bash
cd models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/da/da_DK/talesyntese/medium/da_DK-talesyntese-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/da/da_DK/talesyntese/medium/da_DK-talesyntese-medium.onnx.json
cd ..
```

Both voice models are included in the project and ready to use!

## Usage

### Verify Installation

Check that all dependencies are correctly installed:

```bash
python main.py --verify-environment
```

### Basic Conversion

Convert a PDF to M4B audiobook (output auto-generated in `audio/` folder):

```bash
# Auto-generates: audio/{pdf_name}_{voice_name}.m4b
python main.py input.pdf

# Or specify custom output path
python main.py input.pdf -o output.m4b
```

**Example auto-generated filenames:**
- `audio/document_en_US-lessac-medium.m4b` (English, default)
- `audio/document_da_DK-talesyntese-medium.m4b` (Danish)
- `audio/document_en_US-lessac-medium_test.m4b` (Test run with English)
- `audio/document_da_DK-talesyntese-medium_test.m4b` (Test run with Danish)

### Test Before Full Conversion

Test extraction and voice quality with a random page:

```bash
# Auto-generates output in audio/ folder with "_test" suffix
# Creates: audio/input_en_US-lessac-medium_test.m4b
python main.py input.pdf --test-random-page

# Test with Danish voice
# Creates: audio/input_da_DK-talesyntese-medium_test.m4b
python main.py input.pdf --test-random-page --voice models/da_DK-talesyntese-medium.onnx

# Or specify custom output path
python main.py input.pdf --test-random-page -o test_sample.m4b
```

### Advanced Options

```bash
# Use English voice (default) - auto-saves to audio/document_en_US-lessac-medium.m4b
python main.py input.pdf

# Use Danish voice - auto-saves to audio/document_da_DK-talesyntese-medium.m4b
python main.py input.pdf --voice models/da_DK-talesyntese-medium.onnx

# Adjust speech speed
python main.py input.pdf --speed 1.2

# Danish PDF with faster speech
python main.py dokument.pdf --voice models/da_DK-talesyntese-medium.onnx --speed 1.1

# Use alternate layout engine for complex PDFs
python main.py input.pdf --layout-engine pdfplumber

# Quiet mode (suppress progress output)
python main.py input.pdf --quiet

# Custom output path (bypasses auto-naming)
python main.py input.pdf -o custom/path/output.m4b
```

## Command-Line Options

```
usage: main.py [-h] [--verify-environment] [--test-random-page]
               [-o OUTPUT] [--voice VOICE] [--speed SPEED]
               [--layout-engine {pymupdf,pdfplumber}] [--quiet]
               [input]

Convert PDF documents to M4B audiobooks

positional arguments:
  input                 Input PDF file path

optional arguments:
  -h, --help            Show this help message and exit
  --verify-environment  Verify all dependencies are installed
  --test-random-page    Convert only a random page for testing
  -o OUTPUT, --output OUTPUT
                        Output M4B file path
  --voice VOICE         Path to Piper voice model (.onnx file)
  --speed SPEED         Speech speed multiplier (0.5-2.0, default: 1.0)
  --layout-engine {pymupdf,pdfplumber}
                        PDF extraction engine (default: pymupdf)
  --quiet               Suppress progress output
```

## Project Structure

```
pdf2audio/
├── main.py              # CLI entry point
├── pdf_extractor.py     # PDF text extraction
├── tts_engine.py        # Text-to-speech processing
├── audio_handler.py     # M4B conversion and metadata
├── config.py            # Configuration constants
├── requirements.txt     # Python dependencies
├── models/              # Piper voice models directory
├── audio/               # Generated audiobooks (auto-created)
│   └── {pdf_name}_{voice_name}.m4b
└── README.md            # This file
```

## Troubleshooting

### ffmpeg not found

Ensure ffmpeg is installed and in your system PATH:

```bash
ffmpeg -version
```

If not found, reinstall using the instructions in the Installation section.

### Voice model not found

Download the voice model as described in Installation step 3, or specify the path explicitly:

```bash
python main.py input.pdf -o output.m4b --voice /path/to/voice/model.onnx
```

### Poor text extraction quality

Try using the alternate layout engine:

```bash
python main.py input.pdf -o output.m4b --layout-engine pdfplumber
```

### Scanned PDFs (images only)

This tool extracts text-based PDFs. For scanned documents, use OCR preprocessing tools like:
- Tesseract OCR
- Adobe Acrobat OCR
- Online OCR services

## Performance

- Text extraction: ~1-2 seconds per page
- TTS generation: ~1-3x real-time (10 minutes of audio takes 10-30 minutes)
- Memory usage: ~500MB - 1GB for typical documents

## Known Limitations

- Does not support scanned PDFs without text layer
- Complex multi-column layouts may require manual layout engine selection
- Images and tables are not processed
- Single language per conversion (specify voice with --voice option)

## Voice Models

**Included in this project:**
- `en_US-lessac-medium` - English (US), clear, neutral (default)
- `da_DK-talesyntese-medium` - Danish, natural pronunciation

**Additional Piper voice models available at:**
[https://huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)

Other popular options:
- `en_US-amy-medium` - English (US), female voice, expressive
- `en_GB-alan-medium` - British English, male
- `de_DE-thorsten-medium` - German
- `fr_FR-siwis-medium` - French
- `es_ES-sharvard-medium` - Spanish

## License

This project is for personal and educational use. Check individual dependency licenses for commercial use.

## Contributing

See [REQUIREMENTS.md](REQUIREMENTS.md), [SOLUTION.md](SOLUTION.md), and [PROJECT_PLAN.md](PROJECT_PLAN.md) for technical documentation.

For ideas on future improvements, see [ENHANCEMENTS.md](ENHANCEMENTS.md) which includes:
- Higher quality voice options (Coqui TTS, Bark)
- Translation features (NLLB, OPUS-MT)
- Additional feature suggestions

## Support

For issues and questions, refer to the documentation or check:
- Piper TTS: [https://github.com/rhasspy/piper](https://github.com/rhasspy/piper)
- PyMuPDF: [https://pymupdf.readthedocs.io](https://pymupdf.readthedocs.io)
- ffmpeg: [https://ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html)
