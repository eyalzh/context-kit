"""Tests for binary data handling functionality."""

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest
from mcp import types
from pydantic import AnyUrl

from mcp_client.binary_data_handler import handle_binary_content, save_binary_data_to_file


def test_save_binary_data_to_file():
    """Test saving binary data to file."""
    # Create a temporary directory
    with TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".cxk"
        config_dir.mkdir()

        # Create some test binary data
        test_data = b"test binary data"
        encoded_data = base64.b64encode(test_data).decode("utf-8")

        # Save the data
        file_path = save_binary_data_to_file(config_dir, encoded_data, "image/png", "test")

        # Verify the file was created and contains correct data
        full_path = Path(temp_dir) / file_path
        assert full_path.exists()

        with open(full_path, "rb") as f:
            saved_data = f.read()

        assert saved_data == test_data
        assert file_path.startswith(".cxk/files/test_")
        assert file_path.endswith(".png")


def test_handle_image_content():
    """Test handling ImageContent."""
    with TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".cxk"
        config_dir.mkdir()

        # Create mock ImageContent
        test_data = b"fake image data"
        encoded_data = base64.b64encode(test_data).decode("utf-8")

        image_content = types.ImageContent(type="image", data=encoded_data, mimeType="image/jpeg")

        # Handle the content
        file_path = handle_binary_content(config_dir, image_content)

        # Verify result
        assert file_path
        assert file_path.startswith(".cxk/files/image_")
        assert file_path.endswith(".jpg")  # mimetypes maps image/jpeg to .jpg

        # Verify file contents
        full_path = Path(temp_dir) / file_path
        with open(full_path, "rb") as f:
            saved_data = f.read()
        assert saved_data == test_data


def test_handle_audio_content():
    """Test handling AudioContent."""
    with TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".cxk"
        config_dir.mkdir()

        # Create mock AudioContent
        test_data = b"fake audio data"
        encoded_data = base64.b64encode(test_data).decode("utf-8")

        audio_content = types.AudioContent(
            type="audio",
            data=encoded_data,
            mimeType="audio/mpeg",  # This should map to .mp3
        )

        # Handle the content
        file_path = handle_binary_content(config_dir, audio_content)

        # Verify result
        assert file_path
        assert file_path.startswith(".cxk/files/audio_")
        # mimetypes may not always find an extension, so just check prefix
        assert "audio_" in file_path

        # Verify file contents
        full_path = Path(temp_dir) / file_path
        with open(full_path, "rb") as f:
            saved_data = f.read()
        assert saved_data == test_data


def test_handle_blob_resource_contents():
    """Test handling BlobResourceContents."""
    with TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".cxk"
        config_dir.mkdir()

        # Create mock BlobResourceContents
        test_data = b"fake blob data"
        encoded_data = base64.b64encode(test_data).decode("utf-8")

        blob_content = types.BlobResourceContents(
            blob=encoded_data, uri=AnyUrl("test://blob"), mimeType="application/octet-stream"
        )

        # Handle the content
        file_path = handle_binary_content(config_dir, blob_content)

        # Verify result
        assert file_path
        assert file_path.startswith(".cxk/files/blob_")

        # Verify file contents
        full_path = Path(temp_dir) / file_path
        with open(full_path, "rb") as f:
            saved_data = f.read()
        assert saved_data == test_data


def test_handle_unsupported_content():
    """Test handling unsupported content types."""
    with TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".cxk"
        config_dir.mkdir()

        # Create mock unsupported content
        unsupported_content = Mock()

        # Handle the content
        file_path = handle_binary_content(config_dir, unsupported_content)

        # Should return empty string for unsupported types
        assert file_path == ""


def test_save_binary_data_error_handling():
    """Test error handling when save fails."""
    # Use a non-existent directory to trigger an error
    config_dir = Path("/nonexistent/path")

    # This should raise an exception
    with pytest.raises(Exception) as exc_info:
        save_binary_data_to_file(config_dir, "dGVzdA==", "image/png")

    assert "Failed to save binary data" in str(exc_info.value)
