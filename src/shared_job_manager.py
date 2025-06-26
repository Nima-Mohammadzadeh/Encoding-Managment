"""
Shared Job Manager for Encoding Management
This module handles job synchronization between local and shared storage.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
import random


class SharedJobManager:
    def __init__(self, shared_path: str = None, local_path: str = None):
        """
        Initialize the shared job manager.
        
        Args:
            shared_path: Path to the shared directory
            local_path: Path to the local data directory
        """
        if shared_path is None:
            shared_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        
        if local_path is None:
            local_path = "data"
        
        self.shared_path = shared_path
        self.local_path = local_path
        
        # File paths
        self.shared_active_jobs = os.path.join(shared_path, "shared_active_jobs.json")
        self.shared_archived_jobs = os.path.join(shared_path, "shared_archived_jobs.json")
        self.shared_lock = os.path.join(shared_path, ".jobs_sync.lock")
        
        self.local_active_jobs = os.path.join(local_path, "active_jobs.json")
        self.local_archived_jobs = os.path.join(local_path, "archived_jobs.json")
        
        # Sync metadata
        self.sync_metadata_file = os.path.join(local_path, "sync_metadata.json")
        
        # Initialize metadata if it doesn't exist
        self._initialize_sync_metadata()
    
    def _initialize_sync_metadata(self):
        """Initialize sync metadata file."""
        if not os.path.exists(self.sync_metadata_file):
            metadata = {
                "last_sync": None,
                "last_sync_success": False,
                "sync_count": 0,
                "user_name": os.environ.get("USERNAME", "Unknown"),
                "conflicts_resolved": 0,
                "deleted_jobs": {
                    "active": [],
                    "archived": []
                }
            }
            try:
                os.makedirs(os.path.dirname(self.sync_metadata_file), exist_ok=True)
                with open(self.sync_metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                print(f"⚠️  Could not create sync metadata: {e}")
    
    def _acquire_lock(self, max_retries: int = 15, retry_delay: float = 0.3) -> bool:
        """Acquire a file lock for shared operations."""
        for attempt in range(max_retries):
            try:
                if not os.path.exists(self.shared_lock):
                    with open(self.shared_lock, 'w') as f:
                        f.write(f"Locked by {os.environ.get('USERNAME', 'Unknown')} at {datetime.now()}")
                    return True
                else:
                    # Check if lock is stale (older than 20 seconds)
                    lock_age = time.time() - os.path.getmtime(self.shared_lock)
                    if lock_age > 20:
                        os.remove(self.shared_lock)
                        continue
                    
                    time.sleep(retry_delay + random.uniform(0, 0.1))
            except (OSError, IOError):
                time.sleep(retry_delay)
        
        return False
    
    def _release_lock(self):
        """Release the file lock."""
        try:
            if os.path.exists(self.shared_lock):
                os.remove(self.shared_lock)
        except (OSError, IOError):
            pass
    
    def _load_jobs_file(self, file_path: str) -> List[Dict]:
        """Load jobs from a JSON file."""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"⚠️  Error loading {file_path}: {e}")
            return []
    
    def _save_jobs_file(self, file_path: str, jobs: List[Dict]) -> bool:
        """Save jobs to a JSON file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(jobs, f, indent=2)
            return True
        except Exception as e:
            print(f"⚠️  Error saving {file_path}: {e}")
            return False
    
    def _merge_jobs(self, local_jobs: List[Dict], shared_jobs: List[Dict], job_type: str = "active") -> Tuple[List[Dict], int]:
        """
        Merge local and shared jobs, respecting local deletions and additions.
        
        Args:
            local_jobs: Jobs from local storage
            shared_jobs: Jobs from shared storage
            job_type: "active" or "archived" for deletion tracking
            
        Returns:
            Tuple of (merged_jobs, conflicts_count)
        """
        merged = {}
        conflicts = 0
        
        # Create job signatures for conflict detection
        def job_signature(job):
            return f"{job.get('Customer', '')}-{job.get('Job Ticket#', '')}-{job.get('PO#', '')}"
        
        # Load deleted jobs list from metadata
        deleted_jobs = self._get_deleted_jobs(job_type)
        
        # Step 1: Add all local jobs (these are the current state we want to preserve)
        for job in local_jobs:
            sig = job_signature(job)
            job['_source'] = 'local'
            job['_sync_timestamp'] = datetime.now().isoformat()
            merged[sig] = job
        
        # Step 2: Add shared jobs ONLY if they're not in our deleted list and not already local
        for job in shared_jobs:
            sig = job_signature(job)
            
            # Skip jobs that were intentionally deleted locally
            if sig in deleted_jobs:
                continue
                
            job['_source'] = 'shared'
            job['_sync_timestamp'] = datetime.now().isoformat()
            
            if sig in merged:
                # Conflict: same job exists locally and in shared
                local_job = merged[sig]
                shared_job = job
                
                # Use status and timestamp to decide priority
                local_status = local_job.get('Status', 'New')
                shared_status = shared_job.get('Status', 'New')
                
                # Prefer jobs that are further along in the process
                status_priority = {'New': 1, 'In Progress': 2, 'On Hold': 2, 'Completed': 3, 'Cancelled': 1}
                
                local_priority = status_priority.get(local_status, 1)
                shared_priority = status_priority.get(shared_status, 1)
                
                if shared_priority > local_priority:
                    merged[sig] = shared_job
                    merged[sig]['_conflict_resolved'] = 'shared_preferred'
                    conflicts += 1
                elif shared_priority < local_priority:
                    merged[sig]['_conflict_resolved'] = 'local_preferred'
                    conflicts += 1
                else:
                    # Same priority - prefer local (user's current work)
                    merged[sig]['_conflict_resolved'] = 'local_preferred'
                    conflicts += 1
                
            else:
                # New job from shared that doesn't exist locally - add it
                merged[sig] = job
        
        return list(merged.values()), conflicts
    
    def _get_deleted_jobs(self, job_type: str) -> set:
        """Get set of job signatures that were deleted locally."""
        try:
            with open(self.sync_metadata_file, 'r') as f:
                metadata = json.load(f)
                deleted_list = metadata.get("deleted_jobs", {}).get(job_type, [])
                return set(deleted_list)
        except:
            return set()
    
    def track_job_deletion(self, job: Dict, job_type: str):
        """Track that a job was intentionally deleted locally."""
        def job_signature(job):
            return f"{job.get('Customer', '')}-{job.get('Job Ticket#', '')}-{job.get('PO#', '')}"
        
        try:
            # Load current metadata
            try:
                with open(self.sync_metadata_file, 'r') as f:
                    metadata = json.load(f)
            except:
                metadata = {"deleted_jobs": {"active": [], "archived": []}}
            
            # Ensure structure exists
            if "deleted_jobs" not in metadata:
                metadata["deleted_jobs"] = {"active": [], "archived": []}
            if job_type not in metadata["deleted_jobs"]:
                metadata["deleted_jobs"][job_type] = []
            
            # Add job signature to deleted list
            sig = job_signature(job)
            if sig not in metadata["deleted_jobs"][job_type]:
                metadata["deleted_jobs"][job_type].append(sig)
                
                # Save updated metadata
                with open(self.sync_metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                    
        except Exception as e:
            print(f"⚠️  Could not track job deletion: {e}")
    
    def clear_deletion_tracking(self):
        """Clear deletion tracking (call after successful sync to shared)."""
        try:
            with open(self.sync_metadata_file, 'r') as f:
                metadata = json.load(f)
            
            metadata["deleted_jobs"] = {"active": [], "archived": []}
            
            with open(self.sync_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Could not clear deletion tracking: {e}")
    
    def is_shared_available(self) -> bool:
        """Check if the shared drive is accessible."""
        try:
            return os.path.exists(self.shared_path) and os.access(self.shared_path, os.W_OK)
        except:
            return False
    
    def sync_jobs(self) -> Dict[str, Any]:
        """
        Synchronize jobs between local and shared storage.
        
        Returns:
            Dict with sync results and statistics
        """
        start_time = time.time()
        result = {
            "success": False,
            "message": "",
            "stats": {
                "active_jobs_local": 0,
                "active_jobs_shared": 0,
                "active_jobs_merged": 0,
                "archived_jobs_local": 0,
                "archived_jobs_shared": 0,
                "archived_jobs_merged": 0,
                "conflicts_resolved": 0,
                "sync_duration": 0
            }
        }
        
        # Check if shared drive is available
        if not self.is_shared_available():
            result["message"] = f"Shared drive not accessible: {self.shared_path}"
            return result
        
        # Try to acquire lock
        if not self._acquire_lock():
            result["message"] = "Could not acquire sync lock - another user may be syncing"
            return result
        
        try:
            # Load all job files
            local_active = self._load_jobs_file(self.local_active_jobs)
            local_archived = self._load_jobs_file(self.local_archived_jobs)
            shared_active = self._load_jobs_file(self.shared_active_jobs)
            shared_archived = self._load_jobs_file(self.shared_archived_jobs)
            
            result["stats"]["active_jobs_local"] = len(local_active)
            result["stats"]["active_jobs_shared"] = len(shared_active)
            result["stats"]["archived_jobs_local"] = len(local_archived)
            result["stats"]["archived_jobs_shared"] = len(shared_archived)
            
            # Merge jobs with deletion tracking
            merged_active, active_conflicts = self._merge_jobs(local_active, shared_active, "active")
            merged_archived, archived_conflicts = self._merge_jobs(local_archived, shared_archived, "archived")
            
            total_conflicts = active_conflicts + archived_conflicts
            result["stats"]["conflicts_resolved"] = total_conflicts
            result["stats"]["active_jobs_merged"] = len(merged_active)
            result["stats"]["archived_jobs_merged"] = len(merged_archived)
            
            # Save merged jobs back to both local and shared
            success = True
            success &= self._save_jobs_file(self.local_active_jobs, merged_active)
            success &= self._save_jobs_file(self.local_archived_jobs, merged_archived)
            success &= self._save_jobs_file(self.shared_active_jobs, merged_active)
            success &= self._save_jobs_file(self.shared_archived_jobs, merged_archived)
            
            if success:
                # Clear deletion tracking since changes are now synced to shared
                self.clear_deletion_tracking()
                
                # Update sync metadata
                metadata = {
                    "last_sync": datetime.now().isoformat(),
                    "last_sync_success": True,
                    "sync_count": self._get_sync_count() + 1,
                    "user_name": os.environ.get("USERNAME", "Unknown"),
                    "conflicts_resolved": self._get_conflicts_resolved() + total_conflicts,
                    "deleted_jobs": {"active": [], "archived": []}
                }
                self._save_jobs_file(self.sync_metadata_file, metadata)
                
                result["success"] = True
                result["message"] = f"Sync completed successfully"
                if total_conflicts > 0:
                    result["message"] += f" ({total_conflicts} conflicts resolved)"
                
            else:
                result["message"] = "Failed to save some files during sync"
                
        except Exception as e:
            result["message"] = f"Sync error: {str(e)}"
            
        finally:
            self._release_lock()
            result["stats"]["sync_duration"] = round(time.time() - start_time, 2)
        
        return result
    
    def _get_sync_count(self) -> int:
        """Get the current sync count from metadata."""
        try:
            with open(self.sync_metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get("sync_count", 0)
        except:
            return 0
    
    def _get_conflicts_resolved(self) -> int:
        """Get the total conflicts resolved from metadata."""
        try:
            with open(self.sync_metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get("conflicts_resolved", 0)
        except:
            return 0
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get the current sync status and statistics."""
        try:
            with open(self.sync_metadata_file, 'r') as f:
                metadata = json.load(f)
        except:
            metadata = {}
        
        return {
            "shared_available": self.is_shared_available(),
            "last_sync": metadata.get("last_sync"),
            "last_sync_success": metadata.get("last_sync_success", False),
            "sync_count": metadata.get("sync_count", 0),
            "conflicts_resolved": metadata.get("conflicts_resolved", 0),
            "user_name": metadata.get("user_name", "Unknown"),
            "shared_path": self.shared_path
        }


# Global instance
_shared_job_manager = None


def initialize_shared_job_manager(shared_path: str = None, local_path: str = None) -> bool:
    """Initialize the global shared job manager."""
    global _shared_job_manager
    
    try:
        _shared_job_manager = SharedJobManager(shared_path, local_path)
        return True
    except Exception as e:
        print(f"❌ Error initializing shared job manager: {e}")
        return False


def sync_jobs() -> Dict[str, Any]:
    """Sync jobs using the global manager."""
    if _shared_job_manager is None:
        return {"success": False, "message": "Shared job manager not initialized"}
    
    return _shared_job_manager.sync_jobs()


def get_sync_status() -> Dict[str, Any]:
    """Get sync status using the global manager."""
    if _shared_job_manager is None:
        return {"success": False, "message": "Shared job manager not initialized"}
    
    return _shared_job_manager.get_sync_status()


def is_shared_available() -> bool:
    """Check if shared drive is available."""
    if _shared_job_manager is None:
        return False
    
    return _shared_job_manager.is_shared_available()


def track_job_deletion(job: Dict, job_type: str):
    """Track that a job was intentionally deleted locally."""
    if _shared_job_manager is None:
        return
    
    _shared_job_manager.track_job_deletion(job, job_type) 