import os
from azure.storage.blob import (BlobServiceClient, ContentSettings, PublicAccess)

MIME_MAP = {
    ".html": "text/html",
    ".htm":  "text/html",
    ".js":   "application/javascript",
    ".css":  "text/css",
    ".json": "application/json",
    ".bin":  "application/octet-stream",
    ".laz":  "application/octet-stream",
    ".las":  "application/octet-stream",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
}

def _guess_content_type(name: str) -> ContentSettings | None:
    ext = os.path.splitext(name)[1].lower()
    ct = MIME_MAP.get(ext)
    return ContentSettings(content_type=ct) if ct else None

class AzureStorageManager:
    def __init__(self, container_name: str):
        connection_string = os.getenv("AZURE_CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.container_name = container_name
        self.account_name = self.blob_service_client.account_name

        # Create public container if it doesn't exist
        try:
            self.container_client.get_container_properties()
            print(f"Connected to Azure container: {container_name}")
        except Exception:
            # Create container with public blob access
            self.container_client.create_container(public_access=PublicAccess.Blob)
            print(f"Created public Azure container: {container_name}")

    # ---------- Upload ----------
    def upload_file(self, file_path: str, blob_name: str, timeout: int = 3600):
        """
        Upload a file to Azure Blob Storage with chunked upload for large files.
        
        Uses the blob client's upload_blob method which automatically handles
        chunking for files larger than 256MB. This prevents memory issues and
        provides better reliability for large file uploads.
        
        Args:
            file_path: Local file path to upload
            blob_name: Destination blob name in container
            timeout: Upload timeout in seconds (default: 3600 = 1 hour)
        """
        blob_client = self.container_client.get_blob_client(blob_name)
        
        with open(file_path, "rb") as data:
            # Azure SDK automatically chunks files > 256MB
            # max_concurrency allows parallel chunk uploads
            blob_client.upload_blob(
                data,
                overwrite=True,
                timeout=timeout,
                max_concurrency=4  # Upload up to 4 chunks in parallel
            )
        print(f"Uploaded {file_path} as blob {blob_name}")

    def upload_folder(self, folder_path: str, blob_prefix: str = ""):
        """
        Upload entire folder maintaining structure with correct MIME types.
        
        Args:
            folder_path: Local folder path to upload
            blob_prefix: Optional prefix for blob names (e.g., "project_id/")
        """
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Maintain folder structure relative to folder_path
                relative_path = os.path.relpath(file_path, folder_path)
                # Normalize path separators for blob storage
                relative_path = relative_path.replace(os.sep, '/')
                blob_name = f"{blob_prefix}{relative_path}" if blob_prefix else relative_path
                
                # Read file and upload with correct content type
                with open(file_path, "rb") as data:
                    content_settings = _guess_content_type(file)
                    self.container_client.upload_blob(
                        name=blob_name,
                        data=data,
                        overwrite=True,
                        content_settings=content_settings
                    )
                print(f"Uploaded {file_path} as blob {blob_name}")


    def upload_bytes(
        self,
        data: bytes,
        blob_name: str,
        content_type: str | None = None,
        overwrite: bool = True,
    ):
        """Uploads bytes and applies content type"""
        self.container_client.upload_blob(
            name=blob_name,
            data=data,
            overwrite=overwrite,
            content_settings=ContentSettings(content_type=content_type)
            if content_type
            else None,
        )

    def upload_thumbnail(self, project_id: str, image_data: bytes) -> str:
        """
        Upload thumbnail PNG to {project_id}/thumbnail.png and return public URL.
        
        Args:
            project_id: The project ID
            image_data: PNG image bytes
            
        Returns:
            Public URL for the uploaded thumbnail
        """
        blob_name = f"{project_id}/thumbnail.png"
        self.upload_bytes(
            data=image_data,
            blob_name=blob_name,
            content_type="image/png",
            overwrite=True
        )
        print(f"Uploaded thumbnail for project {project_id}")
        return self.get_public_url(blob_name)

    # ---------- Public URL Generator ----------
    def get_public_url(self, blob_name: str) -> str:
        """
        Return the public URL for a given blob.
        
        Args:
            blob_name: Name of the blob to generate URL for
            
        Returns:
            Public URL (no authentication required)
        """
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in the container.

        Args:
            blob_name: Name of the blob to check

        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    # ---------- Download / Delete ----------
    def download_file(self, blob_name: str, download_path: str):
        with open(download_path, "wb") as f:
            stream = self.container_client.download_blob(blob_name)
            f.write(stream.readall())
        print(f"Downloaded {blob_name} to {download_path}")

    def delete_blob(self, blob_name: str):
        self.container_client.delete_blob(blob_name)
        print(f"Deleted blob {blob_name}")

    def delete_project_files(self, project_id: str):
        """
        Delete all blobs with prefix {project_id}/.
        
        Args:
            project_id: The project ID whose files should be deleted
        """
        prefix = f"{project_id}/"
        blob_list = self.container_client.list_blobs(name_starts_with=prefix)
        deleted_count = 0
        for blob in blob_list:
            self.container_client.delete_blob(blob.name)
            deleted_count += 1
        print(f"Deleted {deleted_count} blobs for project {project_id}")

    def delete_job_file(self, job_id: str):
        """
        Delete temporary job file at jobs/{job_id}.laz.
        
        Args:
            job_id: The job ID whose file should be deleted
        """
        blob_name = f"jobs/{job_id}.laz"
        try:
            self.container_client.delete_blob(blob_name)
            print(f"Deleted job file {blob_name}")
        except Exception as e:
            print(f"Failed to delete job file {blob_name}: {e}")