from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import logging
from datetime import datetime
import json
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)

class MaterialManager:
    def __init__(self):
        """Initialize connections to S3 and MongoDB"""
        self.s3 = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.mongo_client = MongoClient(settings.MONGODB_URI)
        self.db = self.mongo_client.bot_data
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    async def upload_material(self, file_path: str, metadata: Dict) -> Optional[str]:
        """
        Upload material to S3 and save metadata to MongoDB
        :param file_path: Path to file
        :param metadata: Dict with title, description, category, tags
        :return: Material ID if successful
        """
        try:
            # Generate unique filename
            filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
            
            # Upload to S3
            self.s3.upload_file(
                file_path,
                self.bucket_name,
                f"materials/{filename}",
                ExtraArgs={'ACL': 'public-read'}
            )

            # Generate public URL
            file_url = f"https://{self.bucket_name}.s3.amazonaws.com/materials/{filename}"

            # Save metadata to MongoDB
            material_id = self.db.materials.insert_one({
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'category': metadata.get('category', ''),
                'tags': metadata.get('tags', []),
                'file_url': file_url,
                'filename': filename,
                'created_at': datetime.utcnow()
            }).inserted_id

            return str(material_id)

        except Exception as e:
            logger.error(f"Error uploading material: {e}")
            return None

    async def get_material(self, material_id: str) -> Optional[Dict]:
        """Get material metadata by ID"""
        try:
            from bson.objectid import ObjectId
            material = self.db.materials.find_one({'_id': ObjectId(material_id)})
            if material:
                material['id'] = str(material['_id'])
                del material['_id']
            return material
        except Exception as e:
            logger.error(f"Error getting material {material_id}: {e}")
            return None

    async def get_materials_by_tag(self, tag: str) -> List[Dict]:
        """Get materials by tag"""
        try:
            materials = list(self.db.materials.find({'tags': tag}))
            for material in materials:
                material['id'] = str(material['_id'])
                del material['_id']
            return materials
        except Exception as e:
            logger.error(f"Error getting materials by tag {tag}: {e}")
            return []

    async def get_materials_by_category(self, category: str) -> List[Dict]:
        """Get materials by category"""
        try:
            materials = list(self.db.materials.find({'category': category}))
            for material in materials:
                material['id'] = str(material['_id'])
                del material['_id']
            return materials
        except Exception as e:
            logger.error(f"Error getting materials by category {category}: {e}")
            return []

    async def delete_material(self, material_id: str) -> bool:
        """Delete material from S3 and MongoDB"""
        try:
            from bson.objectid import ObjectId
            
            # Get material info
            material = await self.get_material(material_id)
            if not material:
                return False

            # Delete from S3
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=f"materials/{material['filename']}"
            )

            # Delete from MongoDB
            self.db.materials.delete_one({'_id': ObjectId(material_id)})
            return True

        except Exception as e:
            logger.error(f"Error deleting material {material_id}: {e}")
            return False

    async def update_material_metadata(self, material_id: str, metadata: Dict) -> bool:
        """Update material metadata"""
        try:
            from bson.objectid import ObjectId
            result = self.db.materials.update_one(
                {'_id': ObjectId(material_id)},
                {'$set': {
                    'title': metadata.get('title'),
                    'description': metadata.get('description'),
                    'category': metadata.get('category'),
                    'tags': metadata.get('tags'),
                    'updated_at': datetime.utcnow()
                }}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating material {material_id}: {e}")
            return False 