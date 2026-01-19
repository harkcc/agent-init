from mcp.server.fastmcp import FastMCP
from db_connector import MongoDBConnector, get_mongo_config
import logging
from typing import List, Dict, Any, Optional
import json
from bson import json_util
import re

# Initialize FastMCP application
mcp = FastMCP("MongoDB MCP Server")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_json(data):
    """Helper to dump MongoDB documents to JSON format compatible with MCP."""
    return json.loads(json_util.dumps(data))

@mcp.tool()
def list_collections() -> List[str]:
    """
    List all available collections in the configured MongoDB database.
    """
    with MongoDBConnector() as db:
        return db.list_collection_names()

@mcp.tool()
def query_collection(collection_name: str, query: Dict[str, Any] = {}, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query a specific collection with a MongoDB find query.
    
    Args:
        collection_name: The name of the collection to query.
        query: MongoDB query dictionary (e.g. {"status": "active"}). Defaults to empty dict (find all).
        limit: Maximum number of documents to return. Defaults to 10.
    """
    with MongoDBConnector() as db:
        collection = db[collection_name]
        cursor = collection.find(query).limit(limit)
        return parse_json(list(cursor))

@mcp.tool()
def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """
    Get statistics for a specific collection, such as document count.
    """
    with MongoDBConnector() as db:
        collection = db[collection_name]
        count = collection.count_documents({})
        return {
            "collection": collection_name,
            "document_count": count
        }

@mcp.resource("mongo://{collection_name}")
def get_collection_resource(collection_name: str) -> str:
    """
    Read the first 50 documents of a collection as a resource.
    """
    with MongoDBConnector() as db:
        collection = db[collection_name]
        # Limit to 50 for resource reading to prevent overwhelming output
        cursor = collection.find({}).limit(50)
        docs = parse_json(list(cursor))
        return json.dumps(docs, indent=2)

@mcp.tool()
def find_product_by_msku(msku: str) -> List[Dict[str, Any]]:
    """
    Search for a product specifically by its MSKU (Merchant SKU).
    Partial matches are supported (case-insensitive).
    """
    with MongoDBConnector() as db:
        # Assuming 'msku_info' is the collection name based on db_config
        # We need to check if 'msku' or similar field exists. 
        # Based on user request, we assume there is a field for text search.
        # We will try to search in 'msku' field if it exists, or assuming the collection has standard fields.
        # Since I can't see the schema, I will try searching 'msku' field.
        collection = db['msku_info']
        # Regex for partial match, case insensitive
        query = {"msku": {"$regex": msku, "$options": "i"}}
        cursor = collection.find(query).limit(20)
        return parse_json(list(cursor))

@mcp.tool()
def find_product_by_sku(sku: str) -> List[Dict[str, Any]]:
    """
    Search for a product specifically by its SKU.
    Partial matches are supported (case-insensitive).
    """
    with MongoDBConnector() as db:
        collection = db['msku_info']
        # Try searching in 'sku' field (common naming convention)
        # If schema is different, this might need adjustment.
        query = {"sku": {"$regex": sku, "$options": "i"}}
        cursor = collection.find(query).limit(20)
        return parse_json(list(cursor))

if __name__ == "__main__":
    mcp.run()
