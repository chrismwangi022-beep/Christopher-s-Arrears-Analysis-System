"""
Google Drive Handler for Spread Capital Arrears Analysis System
Handles authentication, file uploads, and Google Drive operations using st.secrets
"""

import json
import io
import streamlit as st
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import pandas as pd


class GoogleDriveHandler:
    """Handles Google Drive operations using service account credentials from st.secrets."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self):
        """Initialize Google Drive handler with credentials from st.secrets."""
        self.service = None
        self.authenticated = False
        self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """
        Initialize Google Drive service using credentials from st.secrets.
        
        Expected st.secrets structure:
        {
            "type": "service_account",
            "project_id": "...",
            "private_key_id": "...",
            "private_key": "...",
            "client_email": "...",
            "client_id": "...",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "...",
            "client_x509_cert_url": "..."
        }
        """
        try:
            # Get credentials from st.secrets
            if "google_cloud" not in st.secrets:
                st.warning("Google Cloud credentials not found in st.secrets")
                return False
            
            # Load credentials dictionary
            creds_dict = dict(st.secrets["google_cloud"])
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=self.SCOPES
            )
            
            # Build the service
            self.service = build('drive', 'v3', credentials=credentials)
            self.authenticated = True
            return True
            
        except Exception as e:
            st.error(f"Failed to authenticate with Google Drive: {str(e)}")
            self.authenticated = False
            return False
    
    def upload_file(
        self,
        file_obj: io.BytesIO,
        filename: str,
        folder_id: Optional[str] = None,
        mimetype: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_obj: File object (BytesIO) to upload
            filename: Name of the file to upload
            folder_id: Google Drive folder ID to upload to (optional)
            mimetype: MIME type of the file
            
        Returns:
            File metadata dict if successful, None otherwise
        """
        if not self.authenticated:
            st.error("Not authenticated with Google Drive")
            return None
        
        try:
            # Reset file pointer to beginning
            file_obj.seek(0)
            
            # Create file metadata
            file_metadata = {'name': filename}
            
            # Add to folder if folder_id provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media upload
            media = MediaIoBaseUpload(
                file_obj,
                mimetype=mimetype,
                resumable=True
            )
            
            # Upload file
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, createdTime'
            )
            
            file_metadata = request.execute()
            st.success(f"✓ File '{filename}' uploaded to Google Drive")
            return file_metadata
            
        except Exception as e:
            st.error(f"Error uploading file to Google Drive: {str(e)}")
            return None
    
    def upload_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        folder_id: Optional[str] = None,
        format: str = "excel"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a DataFrame to Google Drive as Excel or CSV file.
        
        Args:
            df: Pandas DataFrame to upload
            filename: Name of the file to upload
            folder_id: Google Drive folder ID to upload to (optional)
            format: 'excel' or 'csv'
            
        Returns:
            File metadata dict if successful, None otherwise
        """
        try:
            # Convert DataFrame to bytes
            buffer = io.BytesIO()
            
            if format.lower() == "excel":
                # Ensure filename ends with .xlsx
                if not filename.lower().endswith('.xlsx'):
                    filename = filename.replace('.csv', '') + '.xlsx'
                
                df.to_excel(buffer, index=False, engine='openpyxl')
                mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                # CSV format
                if not filename.lower().endswith('.csv'):
                    filename = filename.replace('.xlsx', '') + '.csv'
                
                buffer.write(df.to_csv(index=False).encode('utf-8'))
                mimetype = "text/csv"
            
            # Upload using the upload_file method
            return self.upload_file(buffer, filename, folder_id, mimetype)
            
        except Exception as e:
            st.error(f"Error uploading DataFrame: {str(e)}")
            return None
    
    def list_files_in_folder(
        self,
        folder_id: str,
        file_type: Optional[str] = None
    ) -> list:
        """
        List files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            file_type: Optional file type to filter (e.g., 'csv', 'xlsx')
            
        Returns:
            List of file metadata dicts
        """
        if not self.authenticated:
            st.error("Not authenticated with Google Drive")
            return []
        
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            
            if file_type:
                # Add MIME type filter
                mimetype_map = {
                    'csv': 'text/csv',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'xls': 'application/vnd.ms-excel',
                }
                mime = mimetype_map.get(file_type.lower())
                if mime:
                    query += f" and mimeType='{mime}'"
            
            request = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, createdTime, modifiedTime, mimeType)',
                pageSize=100
            )
            
            results = request.execute()
            files = results.get('files', [])
            return files
            
        except Exception as e:
            st.error(f"Error listing files: {str(e)}")
            return []
    
    def get_folder_id_by_name(self, folder_name: str) -> Optional[str]:
        """
        Find a folder ID by name.
        
        Args:
            folder_name: Name of the folder to find
            
        Returns:
            Folder ID if found, None otherwise
        """
        if not self.authenticated:
            st.error("Not authenticated with Google Drive")
            return None
        
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            request = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=10
            )
            
            results = request.execute()
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            return None
            
        except Exception as e:
            st.error(f"Error finding folder: {str(e)}")
            return None
    
    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Parent folder ID (optional)
            
        Returns:
            New folder ID if successful, None otherwise
        """
        if not self.authenticated:
            st.error("Not authenticated with Google Drive")
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            request = self.service.files().create(
                body=file_metadata,
                fields='id'
            )
            
            result = request.execute()
            st.success(f"✓ Folder '{folder_name}' created in Google Drive")
            return result['id']
            
        except Exception as e:
            st.error(f"Error creating folder: {str(e)}")
            return None


def get_drive_handler() -> GoogleDriveHandler:
    """
    Get or initialize the Google Drive handler (singleton pattern).
    Uses Streamlit session state to cache the handler.
    """
    if 'drive_handler' not in st.session_state:
        st.session_state.drive_handler = GoogleDriveHandler()
    return st.session_state.drive_handler
