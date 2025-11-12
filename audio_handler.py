"""
Audio file handler for combining WAV chunks and converting to M4B format
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import os

try:
    from mutagen.mp4 import MP4, MP4Cover
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

from config import (
    AUDIO_CODEC,
    AUDIO_BITRATE,
    CHAPTER_TITLE_TEMPLATE,
    DEFAULT_METADATA,
    TTS_SAMPLE_RATE,
)

logger = logging.getLogger(__name__)


class AudioHandler:
    """Handle audio file operations including M4B conversion"""

    def __init__(self):
        """Initialize audio handler"""
        if not MUTAGEN_AVAILABLE:
            raise ImportError("mutagen is not installed. Install it with: pip install mutagen")

        # Check for ffmpeg
        if not self._check_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found. Please install ffmpeg:\n"
                "  Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Windows: Download from https://ffmpeg.org/download.html"
            )

    @staticmethod
    def _check_ffmpeg() -> bool:
        """Check if ffmpeg is available"""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def combine_wav_files(self, wav_files: List[str], output_path: str) -> str:
        """
        Combine multiple WAV files into one

        Args:
            wav_files: List of WAV file paths
            output_path: Output WAV file path

        Returns:
            Path to combined WAV file
        """
        if not wav_files:
            raise ValueError("No WAV files to combine")

        output_path = Path(output_path)

        if len(wav_files) == 1:
            # Only one file, just copy it
            import shutil
            shutil.copy(wav_files[0], output_path)
            logger.info(f"Single WAV file copied to {output_path}")
            return str(output_path)

        # Create concat file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
            for wav_file in wav_files:
                # Escape single quotes and write absolute path
                escaped_path = str(Path(wav_file).absolute()).replace("'", "'\\''")
                concat_file.write(f"file '{escaped_path}'\n")
            concat_file_path = concat_file.name

        try:
            # Use ffmpeg to concatenate
            logger.info(f"Combining {len(wav_files)} WAV files...")

            subprocess.run([
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c', 'copy',
                '-y',  # Overwrite output file
                str(output_path)
            ], check=True, capture_output=True)

            logger.info(f"Combined WAV saved to {output_path}")
            return str(output_path)

        finally:
            # Clean up concat file
            os.unlink(concat_file_path)

    def convert_to_m4b(
        self,
        wav_file: str,
        output_path: str,
        metadata: Optional[Dict[str, str]] = None,
        chapters: Optional[List[Dict]] = None
    ) -> str:
        """
        Convert WAV to M4B audiobook format with metadata and chapters

        Args:
            wav_file: Input WAV file path
            output_path: Output M4B file path
            metadata: Metadata dictionary (title, author, etc.)
            chapters: List of chapter dictionaries with 'title' and 'start_time' (in seconds)

        Returns:
            Path to generated M4B file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to M4A first (AAC in MP4 container)
        logger.info(f"Converting to M4B format: {output_path}")

        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(wav_file),
            '-c:a', AUDIO_CODEC,
            '-b:a', AUDIO_BITRATE,
            '-ar', str(TTS_SAMPLE_RATE),
            '-ac', '1',  # Mono
        ]

        # Add metadata
        if metadata:
            for key, value in metadata.items():
                if value:
                    ffmpeg_cmd.extend(['-metadata', f'{key}={value}'])

        # Add chapter metadata if provided
        if chapters:
            chapters_file = self._create_chapters_file(chapters)
            try:
                ffmpeg_cmd.extend(['-i', chapters_file, '-map_metadata', '1'])
            except Exception as e:
                logger.warning(f"Failed to add chapters: {e}")
                chapters_file = None
        else:
            chapters_file = None

        ffmpeg_cmd.extend([
            '-y',  # Overwrite output
            str(output_path)
        ])

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"M4B file created: {output_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to convert to M4B: {e.stderr}")

        finally:
            # Clean up chapters file
            if chapters_file and os.path.exists(chapters_file):
                os.unlink(chapters_file)

        # Add additional metadata with mutagen
        self._add_metadata_mutagen(str(output_path), metadata, chapters)

        return str(output_path)

    @staticmethod
    def _create_chapters_file(chapters: List[Dict]) -> str:
        """
        Create ffmpeg metadata file with chapters

        Args:
            chapters: List of chapter dictionaries

        Returns:
            Path to temporary metadata file
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(";FFMETADATA1\n")

            for chapter in chapters:
                start_ms = int(chapter['start_time'] * 1000)
                end_ms = int(chapter.get('end_time', start_ms + 1000) * 1000)

                f.write(f"[CHAPTER]\n")
                f.write(f"TIMEBASE=1/1000\n")
                f.write(f"START={start_ms}\n")
                f.write(f"END={end_ms}\n")
                f.write(f"title={chapter['title']}\n\n")

            return f.name

    def _add_metadata_mutagen(
        self,
        m4b_file: str,
        metadata: Optional[Dict[str, str]],
        chapters: Optional[List[Dict]] = None
    ):
        """
        Add metadata to M4B file using mutagen

        Args:
            m4b_file: Path to M4B file
            metadata: Metadata dictionary
            chapters: Chapter list (optional)
        """
        try:
            audio = MP4(m4b_file)

            # Apply metadata
            if metadata:
                if 'title' in metadata:
                    audio['\xa9nam'] = metadata['title']
                if 'author' in metadata or 'artist' in metadata:
                    author = metadata.get('author', metadata.get('artist', ''))
                    audio['\xa9ART'] = author
                    audio['\xa9alb'] = metadata.get('album', DEFAULT_METADATA['album'])
                if 'album' in metadata:
                    audio['\xa9alb'] = metadata['album']
                if 'genre' in metadata:
                    audio['\xa9gen'] = metadata['genre']
                if 'year' in metadata:
                    audio['\xa9day'] = metadata['year']
                if 'comment' in metadata:
                    audio['\xa9cmt'] = metadata['comment']

                # Mark as audiobook
                audio['stik'] = [2]  # 2 = Audiobook

            audio.save()
            logger.info("Metadata added successfully")

        except Exception as e:
            logger.warning(f"Failed to add metadata with mutagen: {e}")

    def cleanup_temp_files(self, file_paths: List[str]):
        """
        Clean up temporary audio files

        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Deleted temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")


def create_audiobook(
    wav_files: List[str],
    output_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_count: Optional[int] = None,
    cleanup: bool = True
) -> str:
    """
    Convenience function to create M4B audiobook from WAV chunks

    Args:
        wav_files: List of WAV file paths
        output_path: Output M4B file path
        title: Book title
        author: Author name
        page_count: Number of pages (for chapter generation)
        cleanup: Whether to delete temporary files

    Returns:
        Path to generated M4B file
    """
    handler = AudioHandler()

    # Combine WAV files
    combined_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    handler.combine_wav_files(wav_files, combined_wav)

    # Prepare metadata
    metadata = DEFAULT_METADATA.copy()
    if title:
        metadata['title'] = title
    if author:
        metadata['author'] = author

    # Generate chapter markers based on pages
    chapters = None
    if page_count and page_count > 1:
        # For simplicity, distribute chapters evenly
        # In a real implementation, would track actual audio timing
        chapters = []
        # This is a placeholder - actual chapter timing would come from TTS engine
        logger.info("Chapter markers not yet implemented with accurate timing")

    # Convert to M4B
    m4b_file = handler.convert_to_m4b(combined_wav, output_path, metadata, chapters)

    # Cleanup
    if cleanup:
        handler.cleanup_temp_files([combined_wav] + wav_files)

    return m4b_file
