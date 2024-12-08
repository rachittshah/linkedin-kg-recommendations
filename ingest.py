from typing import List, Dict
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.core import Settings
import chromadb
import pandas as pd

class LinkedInDataIngester:
    def __init__(self, neo4j_url: str, neo4j_username: str, neo4j_password: str):
        # Initialize vector store
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma")
        self.chroma_collection = self.chroma_client.create_collection("linkedin_connections")
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # Initialize graph store
        self.graph_store = Neo4jGraphStore(
            username=neo4j_username,
            password=neo4j_password,
            url=neo4j_url,
            database="linkedin"
        )
        
        # Initialize storage context
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store,
            graph_store=self.graph_store
        )
        
        # Initialize node parser
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

    def load_linkedin_data(self, csv_path: str) -> List[Document]:
        """Load LinkedIn data from CSV and convert to Documents"""
        df = pd.read_csv(csv_path)
        documents = []
        
        for _, row in df.iterrows():
            # Create full name from first and last name
            full_name = f"{row['First Name']} {row['Last Name']}"
            
            # Create document text from profile data
            text = f"""
            Name: {full_name}
            Company: {row['Company']}
            URL: {row['URL']}
            Email: {row.get('Email Address', '')}
            Connected On: {row['Connected On']}
            """
            
            # Create metadata
            metadata = {
                "name": full_name,
                "company": row["Company"],
                "linkedin_url": row["URL"],
                "email": row.get("Email Address", ""),
                "connected_on": row["Connected On"],
            }
            
            doc = Document(text=text, metadata=metadata)
            documents.append(doc)
            
        return documents

    def create_knowledge_graph(self, documents: List[Document]):
        """Create knowledge graph from documents"""
        for doc in documents:
            metadata = doc.metadata
            
            # Create Person node
            self.graph_store.query(f"""
                MERGE (p:Person {{name: '{metadata["name"]}'}})
                SET p.email = '{metadata["email"]}',
                    p.linkedin_url = '{metadata["linkedin_url"]}',
                    p.connected_on = '{metadata["connected_on"]}'
            """)
            
            # Create Company node and relationship
            if metadata["company"]:
                self.graph_store.query(f"""
                    MERGE (c:Company {{name: '{metadata["company"]}'}})
                    MERGE (p:Person {{name: '{metadata["name"]}'}})
                    MERGE (p)-[:WORKS_AT]->(c)
                """)

    def build_indexes(self, documents: List[Document]):
        """Build vector index from documents"""
        # Create nodes from documents
        nodes = self.node_parser.get_nodes_from_documents(documents)
        
        # Build vector index
        vector_index = VectorStoreIndex(
            nodes,
            storage_context=self.storage_context
        )
        
        return vector_index 