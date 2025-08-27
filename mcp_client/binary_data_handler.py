import base64
import logging
import mimetypes
from pathlib import Path
from uuid import uuid4

from mcp import types


def save_binary_data_to_file(config_dir: Path, data: str, mime_type: str, file_prefix: str = "binary") -> str:
    """
    Save binary data (base64-encoded) to a file in the config directory.

    Args:
        config_dir: The .cxk config directory path
        data: Base64-encoded binary data
        mime_type: MIME type of the data (e.g., 'image/png', 'audio/wav')
        file_prefix: Prefix for the generated filename

    Returns:
        Relative path to the saved file from the project root

    Raises:
        Exception: If file save fails (errors are logged but not re-raised)
    """
    try:
        # Create files directory if it doesn't exist
        files_dir = config_dir / "files"
        files_dir.mkdir(exist_ok=True)

        # Generate unique filename with appropriate extension
        extension = mimetypes.guess_extension(mime_type) or ""
        filename = f"{file_prefix}_{uuid4().hex[:8]}{extension}"
        file_path = files_dir / filename

        # Decode base64 data and write to file
        binary_data = base64.b64decode(data)
        with open(file_path, "wb") as f:
            f.write(binary_data)

        # Return relative path from project root
        relative_path = file_path.relative_to(config_dir.parent)
        logging.info(f"Saved binary data to {relative_path}")
        return str(relative_path)

    except Exception as e:
        error_msg = f"Failed to save binary data: {e}"
        logging.error(error_msg)
        raise Exception(error_msg) from e


def handle_binary_content(config_dir: Path, content) -> str:
    """
    Handle binary content from MCP responses, saving to file and returning path.

    Args:
        config_dir: The .cxk config directory path
        content: MCP content object (ImageContent, AudioContent, or BlobResourceContents)

    Returns:
        Relative path to the saved file or empty string if handling fails
    """
    try:
        if isinstance(content, types.ImageContent):
            return save_binary_data_to_file(config_dir, content.data, content.mimeType, "image")
        elif isinstance(content, types.AudioContent):
            return save_binary_data_to_file(config_dir, content.data, content.mimeType, "audio")
        elif isinstance(content, types.BlobResourceContents):
            # For blob resources, we don't have mime type info, so we'll save as generic file
            return save_binary_data_to_file(config_dir, content.blob, "application/octet-stream", "blob")
        else:
            logging.warning(f"Unsupported binary content type: {type(content)}")
            return ""
    except Exception as e:
        logging.error(f"Error handling binary content: {e}")
        return ""
