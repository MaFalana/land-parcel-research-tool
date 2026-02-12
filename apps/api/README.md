# Land Parcel Automater API

A FastAPI-based photo management application with MongoDB storage and Azure Blob Storage for images. Supports photo metadata management, filtering by date and tags, geolocation features, and export capabilities.

## Features


## Setup

### Prerequisites

- Python 3.11+
- MongoDB database
- Azure Blob Storage account

### Environment Variables

Create a `.env` file with the following variables:

```env
MONGO_CONNECTION_STRING=your_mongodb_connection_string
MONGO_COLLECTION_NAME=your_database_name
AZURE_STORAGE_CONTAINER_NAME=your_container_name
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
```

### Installation

```bash
pip install -r requirements.txt
```

### Database Setup

For optimal performance when filtering jobs by user, create MongoDB indexes:



### Running the API

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## API Routes





## Frontend Implementation Guide





## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (photo doesn't exist)
- `500`: Internal Server Error (database or storage error)

Example error responses:


## Data Model



## Technology Stack

- FastAPI: Web framework
- MongoDB: Database
- Azure Blob Storage: File storage
- PyMongo: MongoDB driver