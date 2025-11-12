#!/usr/bin/env python3
"""
PDF to Audio Converter - Main CLI Interface
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
import subprocess

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text

from config import (
    DEFAULT_VOICE_MODEL,
    DEFAULT_SPEECH_SPEED,
    PDF_EXTRACTION_ENGINE,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    LOG_FORMAT,
    LOG_LEVEL,
)

from pdf_extractor import PDFExtractor, ExtractionConfidenceWarning
from tts_engine import TTSEngine
from audio_handler import AudioHandler, create_audiobook

# Set up logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL),
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Rich console for better output
console = Console()


def verify_environment() -> bool:
    """
    Verify all dependencies are installed and working

    Returns:
        True if all checks pass
    """
    console.print("\n[bold blue]Checking Dependencies...[/bold blue]\n")

    checks_passed = True

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        console.print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}", style="green")
    else:
        console.print(f"✗ Python version too old: {python_version.major}.{python_version.minor}", style="red")
        checks_passed = False

    # Check ffmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            check=True
        )
        version_line = result.stdout.split('\n')[0]
        console.print(f"✓ {version_line}", style="green")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("✗ ffmpeg not found", style="red")
        console.print("  Install: sudo apt-get install ffmpeg (Ubuntu) or brew install ffmpeg (macOS)", style="yellow")
        checks_passed = False

    # Check Python packages
    packages = {
        'pymupdf': 'PyMuPDF',
        'pdfplumber': 'pdfplumber',
        'piper': 'piper-tts',
        'mutagen': 'mutagen',
        'rich': 'rich',
        'numpy': 'numpy',
    }

    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            console.print(f"✓ {package_name}", style="green")
        except ImportError:
            console.print(f"✗ {package_name} not installed", style="red")
            checks_passed = False

    # Check voice model
    if DEFAULT_VOICE_MODEL.exists():
        console.print(f"✓ Voice model found: {DEFAULT_VOICE_MODEL.name}", style="green")
    else:
        console.print(f"✗ Voice model not found: {DEFAULT_VOICE_MODEL}", style="red")
        console.print(f"  Download from: https://huggingface.co/rhasspy/piper-voices", style="yellow")
        checks_passed = False

    # Summary
    console.print()
    if checks_passed:
        console.print(Panel("[bold green]✓ All dependencies OK[/bold green]", style="green"))
        return True
    else:
        console.print(Panel("[bold red]✗ Some dependencies missing[/bold red]", style="red"))
        return False


def convert_pdf_to_audio(
    pdf_path: str,
    output_path: str,
    voice_model: Optional[str] = None,
    speed: float = DEFAULT_SPEECH_SPEED,
    layout_engine: str = PDF_EXTRACTION_ENGINE,
    test_random_page: bool = False,
    quiet: bool = False
) -> bool:
    """
    Main conversion function

    Args:
        pdf_path: Path to input PDF
        output_path: Path to output M4B file
        voice_model: Path to voice model
        speed: Speech speed multiplier
        layout_engine: PDF extraction engine
        test_random_page: Only convert one random page for testing
        quiet: Suppress progress output

    Returns:
        True if successful
    """
    try:
        # Initialize
        pdf_path = Path(pdf_path)
        output_path = Path(output_path)

        if not pdf_path.exists():
            console.print(f"[red]Error: {ERROR_MESSAGES['pdf_not_found'].format(path=pdf_path)}[/red]")
            return False

        # Get PDF metadata
        title = pdf_path.stem
        console.print(f"\n[bold]Converting:[/bold] {pdf_path.name}")
        console.print(f"[bold]Output:[/bold] {output_path}")
        console.print(f"[bold]Engine:[/bold] {layout_engine}")
        console.print(f"[bold]Speed:[/bold] {speed}x\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            disable=quiet
        ) as progress:

            # Step 1: Extract text from PDF
            task1 = progress.add_task("[cyan]Extracting text from PDF...", total=100)

            extractor = PDFExtractor(pdf_path, engine=layout_engine)

            if test_random_page:
                page_num, text = extractor.extract_random_page()
                text = extractor.preprocess_text(text)
                console.print(f"[green]Testing with page {page_num + 1} of {extractor.page_count}[/green]")
                page_count = 1
            else:
                try:
                    text = extractor.extract_all()
                    page_count = extractor.page_count

                    # Show confidence warnings if any
                    confidence_report = extractor.get_confidence_report()
                    if confidence_report:
                        console.print(Panel(confidence_report, title="[yellow]Extraction Warnings[/yellow]", style="yellow"))

                except ExtractionConfidenceWarning as e:
                    console.print(f"[red]Extraction confidence error: {e}[/red]")
                    return False

            if not text or len(text) < 10:
                console.print(f"[red]{ERROR_MESSAGES['no_text_extracted']}[/red]")
                return False

            progress.update(task1, completed=100)
            console.print(f"[green]✓ Extracted {len(text)} characters from {page_count} page(s)[/green]")

            # Step 2: Convert text to speech
            task2 = progress.add_task("[cyan]Converting text to speech...", total=100)

            tts_engine = TTSEngine(voice_model or str(DEFAULT_VOICE_MODEL), speed)

            # Generate audio chunks
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())
            wav_chunks = tts_engine.synthesize_to_file(text, str(temp_dir / "audio"))

            progress.update(task2, completed=100)
            console.print(f"[green]✓ Generated {len(wav_chunks)} audio chunk(s)[/green]")

            # Step 3: Combine and convert to M4B
            task3 = progress.add_task("[cyan]Creating M4B audiobook...", total=100)

            m4b_file = create_audiobook(
                wav_files=wav_chunks,
                output_path=str(output_path),
                title=title,
                author="Unknown",  # Could extract from PDF metadata
                page_count=page_count,
                cleanup=True
            )

            progress.update(task3, completed=100)

        # Success
        file_size = Path(m4b_file).stat().st_size / (1024 * 1024)  # MB
        console.print(f"\n[bold green]✓ {SUCCESS_MESSAGES['conversion_complete'].format(output=m4b_file)}[/bold green]")
        console.print(f"[dim]File size: {file_size:.2f} MB[/dim]\n")

        return True

    except KeyboardInterrupt:
        console.print("\n[yellow]Conversion cancelled by user[/yellow]")
        return False

    except Exception as e:
        logger.exception("Conversion failed")
        console.print(f"\n[red]Error: {str(e)}[/red]")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert PDF documents to M4B audiobooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf -o audiobook.m4b
  %(prog)s document.pdf --test-random-page -o test.m4b
  %(prog)s document.pdf -o output.m4b --speed 1.2 --layout-engine pdfplumber
  %(prog)s --verify-environment
        """
    )

    parser.add_argument(
        'input',
        nargs='?',
        help='Input PDF file path'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output M4B file path'
    )

    parser.add_argument(
        '--verify-environment',
        action='store_true',
        help='Verify all dependencies are installed'
    )

    parser.add_argument(
        '--test-random-page',
        action='store_true',
        help='Convert only a random page for testing'
    )

    parser.add_argument(
        '--voice',
        help=f'Path to Piper voice model (.onnx file) [default: {DEFAULT_VOICE_MODEL.name}]'
    )

    parser.add_argument(
        '--speed',
        type=float,
        default=DEFAULT_SPEECH_SPEED,
        help=f'Speech speed multiplier (0.5-2.0) [default: {DEFAULT_SPEECH_SPEED}]'
    )

    parser.add_argument(
        '--layout-engine',
        choices=['pymupdf', 'pdfplumber'],
        default=PDF_EXTRACTION_ENGINE,
        help=f'PDF extraction engine [default: {PDF_EXTRACTION_ENGINE}]'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle --verify-environment
    if args.verify_environment:
        success = verify_environment()
        sys.exit(0 if success else 1)

    # Validate input/output arguments
    if not args.input:
        parser.error("Input PDF file is required (or use --verify-environment)")

    if not args.output:
        # Generate output filename from input PDF and voice model
        input_path = Path(args.input)
        pdf_name = input_path.stem

        # Extract voice name from voice model path
        if args.voice:
            voice_path = Path(args.voice)
            voice_name = voice_path.stem.replace('.onnx', '')
        else:
            voice_name = DEFAULT_VOICE_MODEL.stem.replace('.onnx', '')

        # Create audio directory if it doesn't exist
        audio_dir = Path('audio')
        audio_dir.mkdir(exist_ok=True)

        # Generate filename: audio/{pdf_name}_{voice_name}[_test].m4b
        test_suffix = "_test" if args.test_random_page else ""
        args.output = audio_dir / f"{pdf_name}_{voice_name}{test_suffix}.m4b"
        console.print(f"[dim]No output specified, using: {args.output}[/dim]")

    # Perform conversion
    success = convert_pdf_to_audio(
        pdf_path=args.input,
        output_path=args.output,
        voice_model=args.voice,
        speed=args.speed,
        layout_engine=args.layout_engine,
        test_random_page=args.test_random_page,
        quiet=args.quiet
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
