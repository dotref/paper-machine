from fastapi import UploadFile
from pydantic import BaseModel
from typing import Optional, List

class FileMetadata(BaseModel):
    file_name: str
    content_type: str
    # TODO: add other relevant metadata as needed

class FileInfo(BaseModel):
    file: Optional[UploadFile] = None
    file_length: Optional[int] = None
    object_key: str
    metadata: Optional[FileMetadata] = None

class UploadInfo(BaseModel):
    duplicate: bool
    fileinfo: FileInfo

class Response(BaseModel):
    message: str
    fileinfo: FileInfo

# Add these new models for folder operations
class FolderRequest(BaseModel):
    folder_name: str
    folder_path: Optional[str] = None
    
class FolderResponse(BaseModel):
    message: str
    folder_info: dict

class RemoveFolderRequest(BaseModel):
    folder_path: str

class RemoveFolderResponse(BaseModel):
    message: str
    folder_path: str
    removed_objects: List[str]