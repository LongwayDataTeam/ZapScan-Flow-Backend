import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Any, Optional
import json
import os
import re
import uuid
from datetime import datetime
import time

class FirestoreService:
    def __init__(self):
        """Initialize Firestore service"""
        self.db = None
        self._initialize_firestore()
    
    def _initialize_firestore(self):
        """Initialize Firestore connection"""
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Try to use environment variables for Firebase credentials
                if self._get_firebase_credentials_from_env():
                    cred = credentials.Certificate(self._get_firebase_credentials_from_env())
                    firebase_admin.initialize_app(cred)
                else:
                    # Fallback to service account key file
                    service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-service-account.json')
                    if os.path.exists(service_account_path):
                        cred = credentials.Certificate(service_account_path)
                        firebase_admin.initialize_app(cred)
                    else:
                        # Use default credentials (for local development or GCP)
                        firebase_admin.initialize_app()
            
            self.db = firestore.client()
            print("Firestore initialized successfully")
        except Exception as e:
            print(f"Error initializing Firestore: {e}")
            # Fallback to local storage if Firestore fails
            self.db = None
    
    def _get_firebase_credentials_from_env(self) -> dict:
        """Get Firebase credentials from environment variables"""
        required_vars = [
            'FIREBASE_TYPE', 'FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY_ID',
            'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL', 'FIREBASE_CLIENT_ID',
            'FIREBASE_AUTH_URI', 'FIREBASE_TOKEN_URI', 'FIREBASE_AUTH_PROVIDER_X509_CERT_URL',
            'FIREBASE_CLIENT_X509_CERT_URL', 'FIREBASE_UNIVERSE_DOMAIN'
        ]
        
        # Check if all required environment variables are set
        for var in required_vars:
            if not os.getenv(var):
                return None
        
        # Return credentials dictionary
        return {
            "type": os.getenv('FIREBASE_TYPE'),
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": os.getenv('FIREBASE_AUTH_URI'),
            "token_uri": os.getenv('FIREBASE_TOKEN_URI'),
            "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
            "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN')
        }
    
    def _get_collection(self, collection_name: str):
        """Get a Firestore collection reference"""
        if not self.db:
            raise Exception("Firestore not initialized")
        return self.db.collection(collection_name)
    
    def _sanitize_document_id(self, document_id: str) -> str:
        """Sanitize document ID for Firestore"""
        import re
        # Replace invalid characters with underscores
        # Firestore document IDs cannot contain: /, \, ., *, [, ], #, ?, @, :, <, >, |, space
        sanitized = re.sub(r'[\/\\\.\*\[\]\#\?\@\:\<\>\|\s]', '_', document_id)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'doc_' + str(uuid.uuid4())[:8]
        return sanitized
    
    def save_scan(self, scan_data: Dict[str, Any]) -> str:
        """Save a scan record to Firestore"""
        try:
            collection = self._get_collection('scans')
            # Generate unique ID if not provided
            if 'id' not in scan_data:
                scan_data['id'] = str(uuid.uuid4())
            
            # Add timestamp if not present
            if 'timestamp' not in scan_data:
                scan_data['timestamp'] = datetime.now().isoformat()
            
            doc_ref = collection.document(scan_data['id'])
            doc_ref.set(scan_data)
            return scan_data['id']
        except Exception as e:
            print(f"Error saving scan: {e}")
            raise
    
    def get_scans(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all scans from Firestore"""
        try:
            collection = self._get_collection('scans')
            query = collection.order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error getting scans: {e}")
            return []
    
    def get_scans_by_type(self, scan_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get scans by type"""
        try:
            collection = self._get_collection('scans')
            query = collection.where('scan_type', '==', scan_type).order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error getting scans by type: {e}")
            return []
    
    def save_tracker_status(self, tracker_code: str, status_data: Dict[str, Any]):
        """Save tracker status to Firestore"""
        try:
            # Validate tracker_code for Firestore document ID
            if not tracker_code or len(tracker_code) == 0:
                raise ValueError("Tracker code cannot be empty")
            
            # Sanitize tracker_code for Firestore document ID
            sanitized_tracker_code = self._sanitize_document_id(tracker_code)
            
            collection = self._get_collection('tracker_status')
            doc_ref = collection.document(sanitized_tracker_code)
            doc_ref.set(status_data)
        except Exception as e:
            # Error saving tracker status - silent for performance
            raise
    
    def get_tracker_status(self, tracker_code: str) -> Optional[Dict[str, Any]]:
        """Get tracker status from Firestore"""
        try:
            # Sanitize tracker_code for Firestore document ID
            sanitized_tracker_code = self._sanitize_document_id(tracker_code)
            
            collection = self._get_collection('tracker_status')
            doc_ref = collection.document(sanitized_tracker_code)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            # Error getting tracker status - silent for performance
            return None
    
    def get_all_tracker_status(self) -> Dict[str, Any]:
        """Get all tracker statuses"""
        try:
            collection = self._get_collection('tracker_status')
            docs = collection.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            # Error getting all tracker status - silent for performance
            return {}
    
    def save_uploaded_trackers(self, trackers: List[str]):
        """Save uploaded trackers list to Firestore"""
        try:
            collection = self._get_collection('system')
            doc_ref = collection.document('uploaded_trackers')
            doc_ref.set({'trackers': trackers})
        except Exception as e:
            # Error saving uploaded trackers - silent for performance
            raise
    
    def get_uploaded_trackers(self) -> List[str]:
        """Get uploaded trackers list from Firestore"""
        try:
            collection = self._get_collection('system')
            doc_ref = collection.document('uploaded_trackers')
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get('trackers', [])
            return []
        except Exception as e:
            # Error getting uploaded trackers - silent for performance
            return []
    
    def save_tracker_data(self, tracker_code: str, data: Dict[str, Any]):
        """Save tracker data to Firestore"""
        try:
            # Validate tracker_code for Firestore document ID
            if not tracker_code or len(tracker_code) == 0:
                raise ValueError("Tracker code cannot be empty")
            
            # Sanitize tracker_code for Firestore document ID
            sanitized_tracker_code = self._sanitize_document_id(tracker_code)
            
            collection = self._get_collection('tracker_data')
            doc_ref = collection.document(sanitized_tracker_code)
            doc_ref.set(data)
        except Exception as e:
            # Error saving tracker data - silent for performance
            raise

    def save_tracker_data_batch(self, tracker_data_batch: List[tuple]) -> List[str]:
        """Save multiple tracker data entries in a single batch operation - ULTRA-OPTIMIZED"""
        try:
            if not tracker_data_batch:
                return []
            
            collection = self._get_collection('tracker_data')
            batch = self.db.batch()
            saved_tracker_codes = []
            
            # ULTRA-OPTIMIZED: Process in smaller sub-batches for better performance
            sub_batch_size = 250  # Firestore batch limit is 500, using 250 for safety
            
            for i in range(0, len(tracker_data_batch), sub_batch_size):
                sub_batch = tracker_data_batch[i:i + sub_batch_size]
                sub_batch_codes = []
                
                for tracker_code, data in sub_batch:
                    # Validate tracker_code for Firestore document ID
                    if not tracker_code or len(tracker_code) == 0:
                        continue
                    
                    # Sanitize tracker_code for Firestore document ID
                    sanitized_tracker_code = self._sanitize_document_id(tracker_code)
                    
                    doc_ref = collection.document(sanitized_tracker_code)
                    batch.set(doc_ref, data)
                    sub_batch_codes.append(tracker_code)
                
                # Commit sub-batch immediately for faster processing
                if sub_batch_codes:
                    batch.commit()
                    saved_tracker_codes.extend(sub_batch_codes)
                    # Sub-batch saved tracker data entries
                
                # Create new batch for next sub-batch
                batch = self.db.batch()
            
            print(f"✅ Ultra-optimized batch saved {len(saved_tracker_codes)} tracker data entries")
            return saved_tracker_codes
            
        except Exception as e:
            print(f"Error in ultra-optimized batch save tracker data: {e}")
            raise

    def save_tracker_status_batch(self, status_batch: List[tuple]) -> List[str]:
        """Save multiple tracker status entries in a single batch operation - ULTRA-OPTIMIZED"""
        try:
            if not status_batch:
                return []
            
            collection = self._get_collection('tracker_status')
            batch = self.db.batch()
            saved_tracker_codes = []
            
            # ULTRA-OPTIMIZED: Process in smaller sub-batches for better performance
            sub_batch_size = 250  # Firestore batch limit is 500, using 250 for safety
            
            for i in range(0, len(status_batch), sub_batch_size):
                sub_batch = status_batch[i:i + sub_batch_size]
                sub_batch_codes = []
                
                for tracker_code, status_data in sub_batch:
                    # Validate tracker_code for Firestore document ID
                    if not tracker_code or len(tracker_code) == 0:
                        continue
                    
                    # Sanitize tracker_code for Firestore document ID
                    sanitized_tracker_code = self._sanitize_document_id(tracker_code)
                    
                    doc_ref = collection.document(sanitized_tracker_code)
                    batch.set(doc_ref, status_data)
                    sub_batch_codes.append(tracker_code)
                
                # Commit sub-batch immediately for faster processing
                if sub_batch_codes:
                    batch.commit()
                    saved_tracker_codes.extend(sub_batch_codes)
                    print(f"⚡ Sub-batch saved {len(sub_batch_codes)} tracker status entries")
                
                # Create new batch for next sub-batch
                batch = self.db.batch()
            
            print(f"✅ Ultra-optimized batch saved {len(saved_tracker_codes)} tracker status entries")
            return saved_tracker_codes
            
        except Exception as e:
            print(f"Error in ultra-optimized batch save tracker status: {e}")
            raise
    
    def get_tracker_data(self, tracker_code: str) -> Optional[Dict[str, Any]]:
        """Get tracker data from Firestore"""
        try:
            # Sanitize tracker_code for Firestore document ID
            sanitized_tracker_code = self._sanitize_document_id(tracker_code)
            
            collection = self._get_collection('tracker_data')
            doc_ref = collection.document(sanitized_tracker_code)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting tracker data for tracker_code '{tracker_code}': {e}")
            return None
    
    def get_all_tracker_data(self) -> Dict[str, Any]:
        """Get all tracker data"""
        try:
            collection = self._get_collection('tracker_data')
            docs = collection.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            print(f"Error getting all tracker data: {e}")
            return {}
    
    def save_tracker_scan_count(self, tracking_id: str, count_data: Dict[str, Any]):
        """Save tracker scan count to Firestore"""
        try:
            # Sanitize tracking_id for Firestore document ID
            sanitized_tracking_id = self._sanitize_document_id(tracking_id)
            
            collection = self._get_collection('tracker_scan_count')
            doc_ref = collection.document(sanitized_tracking_id)
            doc_ref.set(count_data)
        except Exception as e:
            print(f"Error saving tracker scan count for tracking_id '{tracking_id}': {e}")
            raise
    
    def get_tracker_scan_count(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Get tracker scan count from Firestore"""
        try:
            # Sanitize tracking_id for Firestore document ID
            sanitized_tracking_id = self._sanitize_document_id(tracking_id)
            
            collection = self._get_collection('tracker_scan_count')
            doc_ref = collection.document(sanitized_tracking_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting tracker scan count for tracking_id '{tracking_id}': {e}")
            return None
    
    def get_all_tracker_scan_count(self) -> Dict[str, Any]:
        """Get all tracker scan counts"""
        try:
            collection = self._get_collection('tracker_scan_count')
            docs = collection.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            print(f"Error getting all tracker scan count: {e}")
            return {}
    
    def save_tracker_scan_progress(self, tracking_id: str, progress_data: Dict[str, Any]):
        """Save tracker scan progress to Firestore"""
        try:
            # Sanitize tracking_id for Firestore document ID
            sanitized_tracking_id = self._sanitize_document_id(tracking_id)
            
            collection = self._get_collection('tracker_scan_progress')
            doc_ref = collection.document(sanitized_tracking_id)
            doc_ref.set(progress_data)
        except Exception as e:
            print(f"Error saving tracker scan progress for tracking_id '{tracking_id}': {e}")
            raise
    
    def get_tracker_scan_progress(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Get tracker scan progress from Firestore"""
        try:
            # Sanitize tracking_id for Firestore document ID
            sanitized_tracking_id = self._sanitize_document_id(tracking_id)
            
            collection = self._get_collection('tracker_scan_progress')
            doc_ref = collection.document(sanitized_tracking_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting tracker scan progress for tracking_id '{tracking_id}': {e}")
            return None
    
    def get_all_tracker_scan_progress(self) -> Dict[str, Any]:
        """Get all tracker scan progress"""
        try:
            collection = self._get_collection('tracker_scan_progress')
            docs = collection.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            print(f"Error getting all tracker scan progress: {e}")
            return {}
    
    def clear_all_data(self):
        """Clear all data from Firestore - OPTIMIZED WITH BATCH OPERATIONS"""
        try:
            print("🧹 Starting optimized data clear...")
            start_time = time.time()
            
            # Clear all collections with batch operations
            collections = ['scans', 'tracker_status', 'uploaded_trackers', 'tracker_data', 'tracker_scan_count', 'tracker_scan_progress']
            total_deleted = 0
            
            for collection_name in collections:
                try:
                    collection = self._get_collection(collection_name)
                    docs = list(collection.stream())
                    
                    if docs:
                        print(f"📦 Clearing {len(docs)} documents from {collection_name}...")
                        
                        # Use batch operations for faster deletion
                        batch_size = 500  # Firestore batch limit
                        for i in range(0, len(docs), batch_size):
                            batch = self.db.batch()
                            batch_docs = docs[i:i + batch_size]
                            
                            for doc in batch_docs:
                                batch.delete(doc.reference)
                            
                            batch.commit()
                            total_deleted += len(batch_docs)
                            
                        print(f"✅ Cleared {len(docs)} documents from {collection_name}")
                    else:
                        print(f"ℹ️ No documents in {collection_name}")
                        
                except Exception as e:
                    print(f"⚠️ Error clearing {collection_name}: {e}")
                    continue
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"⚡ Data clear completed in {processing_time:.2f} seconds")
            print(f"🗑️ Total documents deleted: {total_deleted}")
            print(f"🚀 Performance: {total_deleted/processing_time:.1f} documents/second")
            
        except Exception as e:
            print(f"Error clearing data: {e}")
            raise e

    def clear_all_data_except_pending(self, pending_trackers: List[str]):
        """Clear all data from Firestore except pending shipments - OPTIMIZED WITH BATCH OPERATIONS"""
        try:
            print(f"🧹 Starting optimized data clear (preserving {len(pending_trackers)} pending shipments)...")
            start_time = time.time()
            
            # Get all data first
            all_tracker_data = self.get_all_tracker_data()
            all_tracker_status = self.get_all_tracker_status()
            
            # Clear all collections with batch operations
            collections = ['scans', 'tracker_status', 'uploaded_trackers', 'tracker_data', 'tracker_scan_count', 'tracker_scan_progress']
            total_deleted = 0
            
            for collection_name in collections:
                try:
                    collection = self._get_collection(collection_name)
                    docs = list(collection.stream())
                    
                    if docs:
                        print(f"📦 Clearing {len(docs)} documents from {collection_name}...")
                        
                        # Use batch operations for faster deletion
                        batch_size = 500  # Firestore batch limit
                        for i in range(0, len(docs), batch_size):
                            batch = self.db.batch()
                            batch_docs = docs[i:i + batch_size]
                            
                            for doc in batch_docs:
                                batch.delete(doc.reference)
                            
                            batch.commit()
                            total_deleted += len(batch_docs)
                            
                        print(f"✅ Cleared {len(docs)} documents from {collection_name}")
                    else:
                        print(f"ℹ️ No documents in {collection_name}")
                        
                except Exception as e:
                    print(f"⚠️ Error clearing {collection_name}: {e}")
                    continue
            
            # Restore pending shipments with batch operations
            if pending_trackers:
                print(f"🔄 Restoring {len(pending_trackers)} pending shipments...")
                
                # Prepare batch data for pending shipments
                pending_data_batch = []
                pending_status_batch = []
                
                for tracker_code in pending_trackers:
                    if tracker_code in all_tracker_data:
                        pending_data_batch.append((tracker_code, all_tracker_data[tracker_code]))
                    if tracker_code in all_tracker_status:
                        pending_status_batch.append((tracker_code, all_tracker_status[tracker_code]))
                
                # Execute batch operations for pending shipments
                if pending_data_batch:
                    self.save_tracker_data_batch(pending_data_batch)
                if pending_status_batch:
                    self.save_tracker_status_batch(pending_status_batch)
                
                # Update uploaded trackers list to only include pending ones
                self.save_uploaded_trackers(pending_trackers)
                
                print(f"✅ Restored {len(pending_trackers)} pending shipments")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"⚡ Data clear completed in {processing_time:.2f} seconds")
            print(f"🗑️ Total documents deleted: {total_deleted}")
            print(f"🚀 Performance: {total_deleted/processing_time:.1f} documents/second")
            print(f"📦 {len(pending_trackers)} pending shipments preserved")
            
        except Exception as e:
            print(f"Error clearing data except pending: {e}")
            raise e
    
    def migrate_from_json(self, json_file_path: str = 'data.json'):
        """Migrate data from JSON file to Firestore"""
        try:
            if not os.path.exists(json_file_path):
                print(f"JSON file {json_file_path} not found")
                return
            
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Migrate scans
            for scan in data.get('scans', []):
                self.save_scan(scan)
            
            # Migrate tracker status
            for tracker_code, status in data.get('tracker_status', {}).items():
                self.save_tracker_status(tracker_code, status)
            
            # Migrate uploaded trackers
            uploaded_trackers = data.get('uploaded_trackers', [])
            if uploaded_trackers:
                self.save_uploaded_trackers(uploaded_trackers)
            
            # Migrate tracker data
            for tracker_code, tracker_data in data.get('tracker_data', {}).items():
                self.save_tracker_data(tracker_code, tracker_data)
            
            # Migrate tracker scan count
            for tracking_id, count_data in data.get('tracker_scan_count', {}).items():
                self.save_tracker_scan_count(tracking_id, count_data)
            
            # Migrate tracker scan progress
            for tracking_id, progress_data in data.get('tracker_scan_progress', {}).items():
                self.save_tracker_scan_progress(tracking_id, progress_data)
            
            print("Data migration completed successfully")
        except Exception as e:
            print(f"Error during migration: {e}")
            raise
    
    def delete_tracker_data(self, tracker_code: str):
        """Delete tracker data from Firestore"""
        try:
            sanitized_tracker_code = self._sanitize_document_id(tracker_code)
            collection = self._get_collection('tracker_data')
            doc_ref = collection.document(sanitized_tracker_code)
            doc_ref.delete()
        except Exception as e:
            print(f"Error deleting tracker data for tracker_code '{tracker_code}': {e}")
            raise
    
    def delete_tracker_status(self, tracker_code: str):
        """Delete tracker status from Firestore"""
        try:
            collection = self._get_collection('tracker_status')
            doc_id = self._sanitize_document_id(tracker_code)
            collection.document(doc_id).delete()
            print(f"Deleted tracker status for {tracker_code}")
        except Exception as e:
            print(f"Error deleting tracker status: {e}")



# Global instance
firestore_service = FirestoreService() 