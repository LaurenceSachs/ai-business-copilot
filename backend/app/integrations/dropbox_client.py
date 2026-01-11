"""
Dropbox integration for file indexing and search.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import dropbox
from dropbox.files import FileMetadata, FolderMetadata, SearchMatch
from app.core.config import settings


class DropboxService:
    """Service for interacting with Dropbox API."""

    def __init__(self):
        """Initialize Dropbox client with OAuth token."""
        self.client = dropbox.Dropbox(
            oauth2_refresh_token=settings.DROPBOX_REFRESH_TOKEN,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET,
        )

    def list_files(
        self,
        path: str = "",
        recursive: bool = True,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files in Dropbox.

        Args:
            path: Folder path to list (empty string for root)
            recursive: Whether to list recursively
            limit: Maximum number of files to return

        Returns:
            List of file metadata dictionaries
        """
        files = []

        try:
            if recursive:
                result = self.client.files_list_folder(path, recursive=True, limit=limit)
            else:
                result = self.client.files_list_folder(path, limit=limit)

            while True:
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        files.append({
                            "id": entry.id,
                            "path": entry.path_display,
                            "name": entry.name,
                            "size": entry.size,
                            "modified_date": entry.client_modified,
                            "content_hash": entry.content_hash,
                        })

                if not result.has_more:
                    break

                result = self.client.files_list_folder_continue(result.cursor)

        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Dropbox API error: {str(e)}")

        return files

    def download_file(self, path: str) -> bytes:
        """
        Download file content.

        Args:
            path: File path in Dropbox

        Returns:
            File content as bytes
        """
        try:
            metadata, response = self.client.files_download(path)
            return response.content
        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Failed to download file: {str(e)}")

    def download_file_as_text(self, path: str) -> str:
        """
        Download file and decode as text.

        Args:
            path: File path in Dropbox

        Returns:
            File content as text

        Note:
            Only works for text-based files. Binary files may raise UnicodeDecodeError.
        """
        content = self.download_file(path)
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other common encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            raise Exception(f"Unable to decode file as text: {path}")

    def search_files(
        self,
        query: str,
        path: str = "",
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for files in Dropbox.

        Args:
            query: Search query string
            path: Optional path to search within
            max_results: Maximum number of results

        Returns:
            List of matching file metadata
        """
        try:
            results = self.client.files_search_v2(
                query=query,
                options=dropbox.files.SearchOptions(
                    path=path,
                    max_results=max_results,
                )
            )

            matches = []
            for match in results.matches:
                if isinstance(match.metadata, dropbox.files.FileMetadataReference):
                    metadata = match.metadata.metadata
                    if isinstance(metadata, FileMetadata):
                        matches.append({
                            "id": metadata.id,
                            "path": metadata.path_display,
                            "name": metadata.name,
                            "size": metadata.size,
                            "modified_date": metadata.client_modified,
                            "match_type": match.match_type.get_filename() if match.match_type else "unknown",
                        })

            return matches

        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Dropbox search error: {str(e)}")

    def get_shared_link(self, path: str) -> str:
        """
        Get or create a shared link for a file.

        Args:
            path: File path in Dropbox

        Returns:
            Shared link URL
        """
        try:
            # Try to get existing shared links first
            links = self.client.sharing_list_shared_links(path=path)
            if links.links:
                return links.links[0].url

            # Create new shared link if none exists
            link = self.client.sharing_create_shared_link_with_settings(path)
            return link.url

        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Failed to create shared link: {str(e)}")

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a specific file.

        Args:
            path: File path in Dropbox

        Returns:
            File metadata dictionary
        """
        try:
            metadata = self.client.files_get_metadata(path)

            if isinstance(metadata, FileMetadata):
                return {
                    "id": metadata.id,
                    "path": metadata.path_display,
                    "name": metadata.name,
                    "size": metadata.size,
                    "modified_date": metadata.client_modified,
                    "content_hash": metadata.content_hash,
                }
            else:
                raise Exception(f"Path is not a file: {path}")

        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Failed to get file metadata: {str(e)}")
