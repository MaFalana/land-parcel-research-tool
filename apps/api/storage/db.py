import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Optional

# Legacy models - not used for parcel jobs
# from models.Project import Project
# from models.Job import Job

from storage.az import AzureStorageManager
from io import BytesIO

#load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.name = os.getenv("NAME") # Name of the database collection and container
        self.az = AzureStorageManager(self.name) # Initialize Azure Storage Manager
        conn = os.getenv("MONGO_CONNECTION_STRING")
        self.client = MongoClient(conn)
        self.db = self.client[self.name]
        print(f'Connected to MongoDB database: {self.name}\n') 
        self.projectsCollection = self.db['Project'] # Get the Project collection from the database
        self.jobsCollection = self.db['Job'] # Get the Job collection from the database
        self.parcelJobsCollection = self.db['ParcelJob'] # Get the ParcelJob collection from the database
        
        # Ensure indexes exist for efficient queries
        self._ensure_indexes()

    def query(self, query):
        #collection = self.db[collection_name]
        return list(self.projectsCollection.find(query))

    def insert(self, document):
        #collection = self.db[collection_name]
        self.projectsCollection.insert_one(document)
        #result = collection.insert_one(document)
        #return result.inserted_id

    def close(self):
        self.client.close()
    
    def _ensure_indexes(self):
        """
        Ensure required indexes exist on collections.
        This is especially important for Azure Cosmos DB which requires
        explicit indexes for sort operations.
        """
        try:
            # Jobs collection indexes
            # Create index on jobs collection for created_at (used for FIFO sorting)
            self.jobsCollection.create_index([("created_at", 1)], background=True)
            print("Ensured index on jobs.created_at")
            
            # Create index on jobs collection for status (used for filtering pending jobs)
            self.jobsCollection.create_index([("status", 1)], background=True)
            print("Ensured index on jobs.status")
            
            # Create compound index for efficient job queries (status + created_at)
            self.jobsCollection.create_index([("status", 1), ("created_at", 1)], background=True)
            print("Ensured compound index on jobs.status+created_at")
            
            # Create index on jobs collection for project_id (used for getting jobs by project)
            self.jobsCollection.create_index([("project_id", 1)], background=True)
            print("Ensured index on jobs.project_id")
            
            # Create index on cancelled field for efficient cancellation checks
            self.jobsCollection.create_index([("cancelled", 1)], background=True)
            print("Ensured index on jobs.cancelled")
            
            # ParcelJob collection indexes
            # Create index on created_at for sorting
            self.parcelJobsCollection.create_index([("created_at", -1)], background=True)
            print("Ensured index on parcel_jobs.created_at")
            
            # Create index on status for filtering
            self.parcelJobsCollection.create_index([("status", 1)], background=True)
            print("Ensured index on parcel_jobs.status")
            
            # Create index on user_id for filtering by user
            self.parcelJobsCollection.create_index([("user_id", 1)], background=True)
            print("Ensured index on parcel_jobs.user_id")
            
            # Create compound index for efficient queries
            self.parcelJobsCollection.create_index([("status", 1), ("created_at", -1)], background=True)
            print("Ensured compound index on parcel_jobs.status+created_at")
            
            # Create compound index for user-specific queries
            self.parcelJobsCollection.create_index([("user_id", 1), ("created_at", -1)], background=True)
            print("Ensured compound index on parcel_jobs.user_id+created_at")
            
            # Projects collection indexes
            # Create index on created_at field (descending) for sorting newest first
            self.projectsCollection.create_index([("created_at", -1)], background=True)
            print("Ensured index on projects.created_at")
            
            # Create index on name field for sorting and filtering
            self.projectsCollection.create_index([("name", 1)], background=True)
            print("Ensured index on projects.name")
            
            # Create index on client field for filtering
            self.projectsCollection.create_index([("client", 1)], background=True)
            print("Ensured index on projects.client")
            
            # Create index on tags field (array index) for efficient tag filtering
            self.projectsCollection.create_index([("tags", 1)], background=True)
            print("Ensured index on projects.tags")
            
            # Create compound index on client and created_at for efficient filtered sorting
            self.projectsCollection.create_index([("client", 1), ("created_at", -1)], background=True)
            print("Ensured compound index on projects.client+created_at")
            
            # Try to create text index on name and description fields for search functionality
            # Note: Azure Cosmos DB for MongoDB may not support text indexes
            try:
                self.projectsCollection.create_index(
                    [("name", "text"), ("description", "text")],
                    background=True,
                    name="text_search_index"
                )
                print("Ensured text index on projects.name+description")
            except Exception as text_index_error:
                # Text indexes not supported (e.g., in Azure Cosmos DB)
                # Search will use regex instead, which still benefits from the name index
                print(f"Note: Text index not supported ({text_index_error}), will use regex-based search")
            
        except Exception as e:
            print(f"Warning: Failed to create indexes: {e}")
            # Don't fail initialization if index creation fails
            pass
        
    # ==========================================
    # LEGACY PROJECT METHODS (Not used for parcel jobs)
    # ==========================================
    # Commented out to avoid dependency on Project model
    # Uncomment if you need these for other features
    
    # async def addProject(self, project: Project):
    #     if self.exists('Project', {'_id': project.id}):
    #         print(f"Project with id {project.id} already exists. Skipping insertion.")
    #         return
    #     else:
    #         print(f"Project with id {project.id} does not exist. Adding new project.")
    #         doc = project._to_dict()
    #         self.projectsCollection.insert_one(doc)
    #         print(f"Added project: {project} with _id {project.id}")

    # def getProjects(self, query):
    #     projects = self.query(query)
    #     print(f"Found projects: {projects}")
    #     return projects

    # def getProjectsList(self, payload: list):
    #     projects = []
    #     for id in payload:
    #         project = self.getProject({'_id': id})
    #         if project:
    #             projects.append(project)
    #     print(f"Found projects: {projects}")
    #     return projects

    # def getProject(self, query) -> Project:
    #     results = self.query(query)
    #     if not results:
    #         return None
    #     project = Project(**results[0])
    #     return project

    # def updateProject(self, project: Project):
    #     doc = project._to_dict()
    #     self.projectsCollection.update_one({'_id': project.id}, {'$set': doc})
    #     print(f"Updated project: {project.name} with id {project.id}")

    # def deleteProject(self, id):
    #     """Deletes both the Mongo document and all Azure blobs for the project."""
    #     project = self.getProject({'_id': id})
    #     if not project:
    #         print(f"Project with id {id} not found")
    #         return False
    #     self.projectsCollection.delete_one({'_id': id})
    #     print(f"Deleted MongoDB record for {id}")
    #     try:
    #         self.az.delete_project_files(id)
    #         print(f"Deleted all Azure files for project {id}")
    #     except Exception as e:
    #         print(f"Azure delete failed for {id}: {e}")
    #     project_name = project.name if hasattr(project, 'name') else id
    #     print(f"Deleted project: {project_name} with id {id}")
    # ==========================================
    # LEGACY PROJECT METHODS (Not used for parcel jobs)
    # ==========================================
    # Commented out to avoid dependency on Project model
    # Uncomment if you need these for other features
    
    # async def addProject(self, project: Project):
    #     ...
    # def getProjects(self, query):
    #     ...
    # def deleteProject(self, id):
    #     ...
    # See git history for full implementation

    def exists(self, collection_name, query): # Checks if a document exists in the database, return boolean
        collection = self.db[collection_name]
        return collection.find_one(query) != None

    # ==========================================
    # LEGACY METHODS (Not used for parcel jobs)
    # ==========================================
    # All Project and Job methods have been removed
    # Parcel jobs use ParcelJob model and are managed in routes/jobs.py
    # See git history for full implementation of legacy methods

    def get_projects_paginated(self, query_filter: dict = None, sort_by: str = "created_at", 
                               sort_order: str = "desc", limit: int = 50, offset: int = 0) -> dict:
        """
        Get paginated projects with filtering and sorting
        
        Args:
            query_filter: MongoDB query filter (default: None, returns all projects)
            sort_by: Field to sort by (created_at, date, name, client)
            sort_order: Sort order (asc or desc)
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            
        Returns:
            dict: {
                'projects': List of project dictionaries,
                'total': Total count of projects matching the filter
            }
        """
        # Default to empty filter if none provided
        if query_filter is None:
            query_filter = {}
        
        # Convert sort_order to MongoDB format
        sort_direction = -1 if sort_order == "desc" else 1
        
        # Build aggregation pipeline
        pipeline = []
        
        # Stage 1: Match filter
        if query_filter:
            pipeline.append({'$match': query_filter})
        
        # Stage 2: Add fields to handle null values in sorting
        # Null values should be placed at the end regardless of sort order
        # We create a sort_field that replaces null with a value that sorts last
        if sort_by in ['date', 'name', 'client']:
            # For text fields, use empty string for nulls (sorts last in ascending, first in descending)
            # For date fields, use a far future/past date
            if sort_by == 'date':
                # Use a far future date for nulls when descending, far past when ascending
                null_replacement = datetime(9999, 12, 31) if sort_order == "desc" else datetime(1970, 1, 1)
            else:
                # For text fields, use a value that sorts last
                null_replacement = "zzzzzzzzz" if sort_order == "asc" else ""
            
            pipeline.append({
                '$addFields': {
                    f'{sort_by}_sort': {
                        '$ifNull': [f'${sort_by}', null_replacement]
                    }
                }
            })
            sort_field = f'{sort_by}_sort'
        else:
            # For created_at, nulls are unlikely but handle them anyway
            sort_field = sort_by
        
        # Stage 3: Sort with primary and secondary sort
        # Primary sort by the requested field, secondary sort by created_at desc for consistency
        sort_stage = {
            '$sort': {
                sort_field: sort_direction
            }
        }
        
        # Add secondary sort by created_at if not already sorting by it
        if sort_by != 'created_at':
            sort_stage['$sort']['created_at'] = -1
        
        pipeline.append(sort_stage)
        
        # Stage 4: Facet to get both paginated results and total count
        pipeline.append({
            '$facet': {
                'projects': [
                    {'$skip': offset},
                    {'$limit': limit}
                ],
                'total_count': [
                    {'$count': 'count'}
                ]
            }
        })
        
        # Execute aggregation with collation for case-insensitive text sorting
        collation = {
            'locale': 'en',
            'strength': 2  # Case-insensitive comparison
        }
        
        try:
            results = list(self.projectsCollection.aggregate(pipeline, collation=collation))
        except Exception as e:
            # If collation fails (e.g., not supported), try without it
            print(f"Warning: Collation not supported, using default sorting: {e}")
            results = list(self.projectsCollection.aggregate(pipeline))
        
        # Extract results
        if results:
            projects = results[0].get('projects', [])
            total_count_list = results[0].get('total_count', [])
            total = total_count_list[0]['count'] if total_count_list else 0
        else:
            projects = []
            total = 0
        
        print(f"Retrieved {len(projects)} projects (offset: {offset}, limit: {limit}, total: {total})")
        
        return {
            'projects': projects,
            'total': total
        }


    def get_statistics(self) -> dict:
        """
        Get aggregated statistics for the dashboard
        
        Returns:
            dict: {
                'total_projects': Total number of projects,
                'total_points': Sum of all point counts,
                'active_jobs': Count of pending/processing jobs,
                'completed_jobs_24h': Count of jobs completed in last 24 hours,
                'failed_jobs_24h': Count of jobs failed in last 24 hours
            }
        """
        try:
            # Count total projects
            total_projects = self.projectsCollection.count_documents({})
            
            # Calculate total points using aggregation pipeline
            # Handle null point_count values by treating them as 0
            points_pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total': {
                            '$sum': {
                                '$ifNull': ['$point_count', 0]
                            }
                        }
                    }
                }
            ]
            
            points_result = list(self.projectsCollection.aggregate(points_pipeline))
            total_points = points_result[0]['total'] if points_result else 0
            
            # Count active jobs (status in pending, processing)
            active_jobs = self.jobsCollection.count_documents({
                'status': {'$in': ['pending', 'processing']}
            })
            
            # Count completed jobs in last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            completed_jobs_24h = self.jobsCollection.count_documents({
                'status': 'completed',
                'completed_at': {'$gte': cutoff_time}
            })
            
            # Count failed jobs in last 24 hours
            failed_jobs_24h = self.jobsCollection.count_documents({
                'status': 'failed',
                'completed_at': {'$gte': cutoff_time}
            })
            
            statistics = {
                'total_projects': total_projects,
                'total_points': total_points,
                'active_jobs': active_jobs,
                'completed_jobs_24h': completed_jobs_24h,
                'failed_jobs_24h': failed_jobs_24h
            }
            
            print(f"Retrieved statistics: {statistics}")
            return statistics
            
        except Exception as e:
            print(f"Error retrieving statistics: {e}")
            raise


    # Ortho Management Methods

    def update_project_ortho(self, project_id: str, url: str, thumbnail_url: Optional[str] = None, bounds: Optional[List[List[float]]] = None) -> bool:
        """
        Update project with ortho URLs and bounds
        
        Args:
            project_id: The project ID to update
            url: Public URL to the ortho PNG overlay
            thumbnail_url: Optional public URL to the thumbnail PNG
            bounds: Optional Leaflet bounds [[south, west], [north, east]]
            
        Returns:
            bool: True if project was updated successfully, False if project not found
        """
        # Build the ortho object
        ortho_data = {
            'url': url,
            'thumbnail': thumbnail_url,
            'bounds': bounds
        }
        
        # Update the project document
        result = self.projectsCollection.update_one(
            {'_id': project_id},
            {
                '$set': {
                    'ortho': ortho_data,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            print(f"Project {project_id} not found, cannot update ortho")
            return False
        
        if result.modified_count > 0:
            print(f"Updated ortho for project {project_id}")
            return True
        else:
            print(f"Project {project_id} ortho already up to date")
            return True