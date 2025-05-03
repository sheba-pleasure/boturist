from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
import os
from io import BytesIO
from PIL import Image

import boto3
from botocore.exceptions import ClientError
from telegram import Document, InputFile, PhotoSize, Video

from config import Config
from database import Database

logger = logging.getLogger(__name__)

class ContentManager:
    """Content and materials management class"""
    
    def __init__(self, db: Database):
        """Initialize content manager"""
        self.db = db
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_CONFIG['aws_access_key_id'],
            aws_secret_access_key=Config.AWS_CONFIG['aws_secret_access_key']
        )
        self.bucket_name = Config.AWS_CONFIG['bucket_name']
    
    async def upload_material(self, file_path: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Upload material to S3 and save metadata to database"""
        try:
            # Generate S3 key
            file_name = os.path.basename(file_path)
            s3_key = f"materials/{metadata['category']}/{file_name}"
            
            # Upload to S3
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': self._get_content_type(file_name),
                    'Metadata': {
                        'category': metadata['category'],
                        'title': metadata['title'],
                        'description': metadata.get('description', '')
                    }
                }
            )
            
            # Save to database
            async with self.db.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO materials (title, description, category, file_url)
                    VALUES ($1, $2, $3, $4)
                    """,
                    metadata['title'],
                    metadata.get('description', ''),
                    metadata['category'],
                    f"s3://{self.bucket_name}/{s3_key}"
                )
            
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading material: {e}")
            return None
    
    async def get_material(self, material_id: int) -> Optional[Dict[str, Any]]:
        """Get material metadata and generate download URL"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                material = await conn.fetchrow(
                    """
                    SELECT * FROM materials WHERE id = $1
                    """,
                    material_id
                )
                
                if not material:
                    return None
                
                # Generate presigned URL
                s3_key = material['file_url'].replace(f"s3://{self.bucket_name}/", "")
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
                
                return {
                    'id': material['id'],
                    'title': material['title'],
                    'description': material['description'],
                    'category': material['category'],
                    'download_url': url,
                    'created_at': material['created_at']
                }
                
        except Exception as e:
            logger.error(f"Error getting material: {e}")
            return None
    
    async def get_materials_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all materials in a category"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                materials = await conn.fetch(
                    """
                    SELECT * FROM materials WHERE category = $1
                    ORDER BY created_at DESC
                    """,
                    category
                )
                
                return [dict(m) for m in materials]
                
        except Exception as e:
            logger.error(f"Error getting materials by category: {e}")
            return []
    
    async def delete_material(self, material_id: int) -> bool:
        """Delete material from S3 and database"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                material = await conn.fetchrow(
                    """
                    DELETE FROM materials WHERE id = $1
                    RETURNING file_url
                    """,
                    material_id
                )
                
                if not material:
                    return False
                
                # Delete from S3
                s3_key = material['file_url'].replace(f"s3://{self.bucket_name}/", "")
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            return False
    
    async def search_materials(self, query: str) -> List[Dict[str, Any]]:
        """Search materials by title or description"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                materials = await conn.fetch(
                    """
                    SELECT * FROM materials
                    WHERE title ILIKE $1 OR description ILIKE $1
                    ORDER BY created_at DESC
                    """,
                    f"%{query}%"
                )
                
                return [dict(m) for m in materials]
                
        except Exception as e:
            logger.error(f"Error searching materials: {e}")
            return []
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif'
        }
        return content_types.get(ext, 'application/octet-stream')

class ContentScheduler:
    """Content scheduling and publishing class"""
    
    def __init__(self, db: Database):
        """Initialize content scheduler"""
        self.db = db
    
    async def schedule_post(self, data: Dict[str, Any]) -> bool:
        """Schedule a post for publishing"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO scheduled_posts (
                        platform, content, media_urls, scheduled_time,
                        status, created_at
                    )
                    VALUES ($1, $2, $3, $4, 'pending', CURRENT_TIMESTAMP)
                    """,
                    data['platform'],
                    data['content'],
                    data.get('media_urls', []),
                    data['scheduled_time']
                )
                return True
                
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return False
    
    async def get_pending_posts(self) -> List[Dict[str, Any]]:
        """Get all pending posts that should be published"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                posts = await conn.fetch(
                    """
                    SELECT * FROM scheduled_posts
                    WHERE status = 'pending'
                    AND scheduled_time <= CURRENT_TIMESTAMP
                    ORDER BY scheduled_time ASC
                    """
                )
                
                return [dict(p) for p in posts]
                
        except Exception as e:
            logger.error(f"Error getting pending posts: {e}")
            return []
    
    async def mark_post_published(self, post_id: int) -> bool:
        """Mark post as published"""
        try:
            async with self.db.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE scheduled_posts
                    SET status = 'published', published_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    post_id
                )
                return True
                
        except Exception as e:
            logger.error(f"Error marking post as published: {e}")
            return False

class RequestFileManager:
    """Manager for request files"""
    
    def __init__(self, db: Database):
        """Initialize request file manager"""
        self.db = db
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_CONFIG['aws_access_key_id'],
            aws_secret_access_key=Config.AWS_CONFIG['aws_secret_access_key']
        )
        self.bucket_name = Config.AWS_CONFIG['bucket_name']
    
    async def save_file(self, request_id: int, file: Document | PhotoSize | Video) -> Optional[Dict[str, Any]]:
        """Save file from Telegram to S3 and database"""
        try:
            # Проверка размера файла
            if not self._check_file_size(file):
                raise ValueError("Файл превышает допустимый размер")
            
            # Проверка типа файла
            if not self._check_file_type(file):
                raise ValueError("Неподдерживаемый тип файла")
            
            # Download file from Telegram
            file_path = await file.get_file()
            file_content = await file_path.download_as_bytearray()
            
            # Generate S3 key
            file_name = getattr(file, 'file_name', f"file_{datetime.now().timestamp()}")
            s3_key = f"requests/{request_id}/{file_name}"
            
            # Create preview for images
            preview_key = None
            if isinstance(file, PhotoSize) or (isinstance(file, Document) and 
                self._get_content_type(file_name).startswith('image/')):
                preview_key = await self._create_preview(file_content, request_id, file_name)
            
            # Upload to S3
            content_type = self._get_content_type(file_name)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Save to database
            file_data = {
                "file_name": file_name,
                "file_type": content_type,
                "file_size": len(file_content),
                "s3_key": s3_key,
                "preview_key": preview_key
            }
            
            file_id = await self.db.add_request_file(request_id, file_data)
            return {"id": file_id, **file_data}
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving request file: {e}")
            return None
    
    def _check_file_size(self, file: Document | PhotoSize | Video) -> bool:
        """Check if file size is within limits"""
        file_size = getattr(file, 'file_size', 0)
        
        if isinstance(file, PhotoSize):
            return file_size <= Config.FILE_SETTINGS['max_photo_size']
        elif isinstance(file, Video):
            return file_size <= Config.FILE_SETTINGS['max_video_size']
        else:
            return file_size <= Config.FILE_SETTINGS['max_file_size']
    
    def _check_file_type(self, file: Document | PhotoSize | Video) -> bool:
        """Check if file type is allowed"""
        if isinstance(file, PhotoSize):
            return True  # Telegram already filters image types
        elif isinstance(file, Video):
            return True  # Telegram already filters video types
        
        if not hasattr(file, 'file_name'):
            return False
        
        content_type = self._get_content_type(file.file_name)
        allowed_types = []
        for types in Config.FILE_SETTINGS['allowed_mime_types'].values():
            allowed_types.extend(types)
        
        return content_type in allowed_types
    
    async def _create_preview(self, file_content: bytes, request_id: int, original_filename: str) -> Optional[str]:
        """Create preview for image files"""
        try:
            # Open image with PIL
            image = Image.open(BytesIO(file_content))
            
            # Calculate new dimensions
            max_size = Config.FILE_SETTINGS['preview_image_size']
            ratio = min(max_size / image.width, max_size / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            
            # Resize image
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to JPEG
            output = BytesIO()
            image.convert('RGB').save(
                output, 
                'JPEG', 
                quality=Config.FILE_SETTINGS['preview_quality']
            )
            preview_content = output.getvalue()
            
            # Generate preview key and upload
            preview_key = f"requests/{request_id}/previews/{os.path.splitext(original_filename)[0]}_preview.jpg"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=preview_key,
                Body=preview_content,
                ContentType='image/jpeg'
            )
            
            return preview_key
            
        except Exception as e:
            logger.error(f"Error creating preview: {e}")
            return None
    
    async def get_file_url(self, file_id: int, preview: bool = False) -> Optional[Dict[str, str]]:
        """Get temporary download URL for file and its preview"""
        try:
            files = await self.db.get_request_files(file_id)
            if not files:
                return None
            
            file = files[0]
            urls = {
                'file_url': self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file['s3_key']
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
            }
            
            # Add preview URL if available
            if preview and file.get('preview_key'):
                urls['preview_url'] = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file['preview_key']
                    },
                    ExpiresIn=3600
                )
            
            return urls
            
        except Exception as e:
            logger.error(f"Error getting file URL: {e}")
            return None
    
    async def delete_file(self, file_id: int) -> bool:
        """Delete file from S3 and database"""
        try:
            files = await self.db.get_request_files(file_id)
            if not files:
                return False
            
            file = files[0]
            
            # Delete main file from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file['s3_key']
            )
            
            # Delete preview if exists
            if file.get('preview_key'):
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file['preview_key']
                )
            
            # Delete from database
            return await self.db.delete_request_file(file_id)
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'txt': 'text/plain',
            'zip': 'application/zip',
            'rar': 'application/x-rar-compressed'
        }
        return content_types.get(ext, 'application/octet-stream') 