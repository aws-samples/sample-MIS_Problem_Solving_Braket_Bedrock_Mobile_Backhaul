import os
import uuid
import shutil
import tempfile
import hashlib
import logging
import time
from datetime import datetime, timedelta
import threading
from io import BytesIO
from PIL import Image
import imghdr


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='file_security.log'
)
logger = logging.getLogger('secure_file_handler')

# Constants
MAX_FILE_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = ['png', 'jpeg', 'jpg']
ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg"]

# Create a secure temporary directory with restricted permissions
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'bedrock_braket_secure_files')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, mode=0o700)  # Only owner can access

# File retention settings
FILE_RETENTION_HOURS = 24  # Files older than this will be deleted
CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour

# Store file metadata for tracking
file_metadata = {}

class SecureFile:
    """Class to handle secure file operations"""
    
    def __init__(self, file_data=None, file_path=None, file_type=None):
        """Initialize with either file data or path"""
        self.file_data = file_data
        self.file_path = file_path
        self.file_type = file_type
        self.file_hash = None
        self.created_at = datetime.now()
        self.last_accessed = self.created_at
        self.size_mb = None
        
        if file_data:
            self.size_mb = len(file_data) / (1024 * 1024)
            self.file_hash = hashlib.sha256(file_data).hexdigest()
            
    def save_to_disk(self):
        """Save file data to secure temporary storage"""
        if not self.file_data:
            logger.error("No file data to save")
            return False
            
        # Create unique filename with hash prefix for tracking
        unique_id = str(uuid.uuid4())
        if not self.file_type:
            self.file_type = imghdr.what(None, h=self.file_data)
            
        filename = f"{self.file_hash[:10]}_{unique_id}.{self.file_type}"
        self.file_path = os.path.join(TEMP_DIR, filename)
        
        try:
            # Write file with secure permissions
            with open(self.file_path, 'wb') as f:
                f.write(self.file_data)
                
            # Set secure permissions (only owner can read/write)
            os.chmod(self.file_path, 0o600)
            
            # Store metadata
            file_metadata[self.file_path] = {
                'hash': self.file_hash,
                'created': self.created_at,
                'accessed': self.last_accessed,
                'size_mb': self.size_mb,
                'type': self.file_type
            }
            
            logger.info(f"File saved securely: {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False
    
    def get_data(self):
        """Get file data, either from memory or disk"""
        if self.file_data:
            self.last_accessed = datetime.now()
            if self.file_path in file_metadata:
                file_metadata[self.file_path]['accessed'] = self.last_accessed
            return self.file_data
            
        if not self.file_path or not os.path.exists(self.file_path):
            logger.warning(f"Attempted to access nonexistent file: {self.file_path}")
            return None
            
        try:
            with open(self.file_path, 'rb') as f:
                self.file_data = f.read()
                
            self.last_accessed = datetime.now()
            if self.file_path in file_metadata:
                file_metadata[self.file_path]['accessed'] = self.last_accessed
                
            return self.file_data
            
        except Exception as e:
            logger.error(f"Error reading file {self.file_path}: {str(e)}")
            return None
    
    def verify_integrity(self):
        """Verify file integrity using stored hash"""
        if not self.file_path or not os.path.exists(self.file_path):
            logger.warning(f"Cannot verify integrity of nonexistent file: {self.file_path}")
            return False
            
        try:
            with open(self.file_path, 'rb') as f:
                file_data = f.read()
                
            current_hash = hashlib.sha256(file_data).hexdigest()
            stored_hash = None
            
            if self.file_path in file_metadata:
                stored_hash = file_metadata[self.file_path]['hash']
            elif self.file_hash:
                stored_hash = self.file_hash
                
            if not stored_hash:
                logger.warning(f"No hash available to verify file: {self.file_path}")
                return False
                
            if current_hash != stored_hash:
                logger.warning(f"File integrity check failed for {self.file_path}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying file integrity: {str(e)}")
            return False
    
    def delete(self):
        """Securely delete the file"""
        if not self.file_path or not os.path.exists(self.file_path):
            return
            
        try:
            # Overwrite file with zeros before deleting (basic secure deletion)
            file_size = os.path.getsize(self.file_path)
            with open(self.file_path, 'wb') as f:
                f.write(b'\0' * file_size)
                
            # Delete the file
            os.remove(self.file_path)
            
            # Remove from metadata
            if self.file_path in file_metadata:
                del file_metadata[self.file_path]
                
            logger.info(f"File securely deleted: {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error deleting file {self.file_path}: {str(e)}")


def validate_and_store_file(file_obj):
    """
    Validates and securely stores an uploaded file
    Returns (is_valid, error_message, secure_file)
    """
    if file_obj is None:
        return False, "No file uploaded", None
        
    try:
        # Get file data
        file_data = file_obj.getvalue()
        
        # Check file size
        file_size_mb = len(file_data) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"File size exceeds limit: {file_size_mb}MB")
            return False, f"File size exceeds maximum allowed ({MAX_FILE_SIZE_MB}MB)", None
        
        # Check file type
        img_format = imghdr.what(None, h=file_data)
        if img_format not in ALLOWED_IMAGE_TYPES:
            logger.warning(f"Invalid image format: {img_format}")
            return False, "File does not appear to be a valid image", None
        
        # Verify it's a valid image with PIL
        try:
            img = Image.open(BytesIO(file_data))
            img.verify()  # Verify it's a valid image
            
            # Reopen the image after verify (which closes it)
            img = Image.open(BytesIO(file_data))
            
            # Check image dimensions
            if img.width > 4000 or img.height > 4000:
                logger.warning(f"Image dimensions too large: {img.width}x{img.height}")
                return False, "Image dimensions too large (max 4000x4000)", None
            
            # Create and store secure file
            secure_file = SecureFile(file_data=file_data, file_type=img_format)
            if secure_file.save_to_disk():
                return True, "", secure_file
            else:
                return False, "Failed to securely store file", None
                
        except Exception as e:
            logger.error(f"Error validating image: {str(e)}")
            return False, f"Invalid image file: {str(e)}", None
            
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        return False, f"Error processing file: {str(e)}", None


def store_generated_image(image_data, image_type="png"):
    """
    Securely store an image generated by the application
    Returns a SecureFile object
    """
    if not image_data:
        logger.error("No image data to store")
        return None
        
    try:
        # Convert BytesIO to bytes if needed
        if hasattr(image_data, 'getvalue'):
            file_data = image_data.getvalue()
        else:
            file_data = image_data
            
        # Create and store secure file
        secure_file = SecureFile(file_data=file_data, file_type=image_type)
        if secure_file.save_to_disk():
            return secure_file
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error storing generated image: {str(e)}")
        return None


def get_file_as_bytesio(secure_file):
    """
    Get file data as BytesIO object for processing
    Returns BytesIO object or None if file not found
    """
    if not secure_file:
        return None
        
    file_data = secure_file.get_data()
    if not file_data:
        return None
        
    file_obj = BytesIO(file_data)
    if secure_file.file_path:
        file_obj.name = os.path.basename(secure_file.file_path)
    else:
        file_obj.name = f"file.{secure_file.file_type}" if secure_file.file_type else "file.bin"
        
    return file_obj


def cleanup_old_files():
    """Remove files older than retention period"""
    cutoff_time = datetime.now() - timedelta(hours=FILE_RETENTION_HOURS)
    files_to_remove = []
    
    # Find old files
    for file_path, metadata in list(file_metadata.items()):
        if metadata['accessed'] < cutoff_time:
            files_to_remove.append(file_path)
    
    # Remove old files
    for file_path in files_to_remove:
        try:
            secure_file = SecureFile(file_path=file_path)
            secure_file.delete()
            logger.info(f"Cleaned up old file: {file_path}")
        except Exception as e:
            logger.error(f"Error during cleanup of {file_path}: {str(e)}")


def cleanup_all_files():
    """Remove all files in the temporary directory"""
    try:
        # Delete all files in the directory
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    # Create a SecureFile object for proper deletion
                    secure_file = SecureFile(file_path=file_path)
                    secure_file.delete()
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")
                    
        logger.info("All temporary files cleaned up")
    except Exception as e:
        logger.error(f"Error during complete cleanup: {str(e)}")


def start_cleanup_scheduler():
    """Start background thread for file cleanup with timer-based scheduling"""
    
    consecutive_errors = 0
    max_backoff = 4 * 3600  # Maximum backoff of 4 hours
    cleanup_timer = None
    
    def cleanup_job():
        nonlocal consecutive_errors, cleanup_timer
        
        try:
            # Run the cleanup
            cleanup_old_files()
            
            # Reset error counter on success
            if consecutive_errors > 0:
                logger.info(f"Cleanup succeeded after {consecutive_errors} consecutive errors")
                consecutive_errors = 0
            
            # Schedule next run with standard interval
            interval = CLEANUP_INTERVAL_SECONDS
            
        except Exception as e:
            # Increment error counter
            consecutive_errors += 1
            
            # Calculate backoff time with exponential increase
            interval = min(CLEANUP_INTERVAL_SECONDS * (2 ** consecutive_errors), max_backoff)
            
            logger.error(f"Error in cleanup task (attempt {consecutive_errors}): {str(e)}")
            logger.info(f"Next cleanup attempt in {interval//60} minutes")
        
        # Schedule next run
        cleanup_timer = threading.Timer(interval, cleanup_job)
        cleanup_timer.daemon = True
        cleanup_timer.start()
    
    # Start first timer
    cleanup_timer = threading.Timer(CLEANUP_INTERVAL_SECONDS, cleanup_job)
    cleanup_timer.daemon = True
    cleanup_timer.start()
    
    logger.info("File cleanup scheduler started with adaptive timing using timer-based approach")


# Start the cleanup scheduler when the module is imported
start_cleanup_scheduler()