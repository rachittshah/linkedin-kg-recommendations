from typing import List, Dict
from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.graph_stores.neo4j import Neo4jGraphStore

class LinkedInAnalyzer:
    def __init__(self, vector_index: VectorStoreIndex, graph_store: Neo4jGraphStore):
        self.vector_index = vector_index
        self.graph_store = graph_store
        
        # Initialize query engines
        self.vector_query_engine = vector_index.as_query_engine(
            similarity_top_k=50,
            node_postprocessors=[
                SimilarityPostprocessor(similarity_cutoff=0.7)
            ]
        )

    def find_interesting_connections(self, criteria: Dict[str, str]) -> List[Dict]:
        """Find interesting connections based on given criteria"""
        # First use graph query to filter initial set
        graph_query = self._build_graph_query(criteria)
        initial_candidates = self.graph_store.query(graph_query)
        
        # Use vector search for semantic matching
        vector_query = self._build_vector_query(criteria)
        vector_results = self.vector_query_engine.query(vector_query)
        
        # Combine results with scoring
        combined_results = self._combine_and_rank_results(
            initial_candidates, 
            vector_results, 
            criteria
        )
        
        return combined_results

    def _combine_and_rank_results(self, graph_results, vector_results, criteria):
        """Combine and rank results based on multiple factors"""
        scores = {}
        
        # Score based on graph results (exact matches)
        for result in graph_results:
            person_name = result['p.name']
            scores[person_name] = scores.get(person_name, 0) + 1.0
            
            # Bonus for matching industry
            if criteria.get('industry') and result.get('i.name') == criteria['industry']:
                scores[person_name] += 0.5
            
            # Bonus for senior roles
            if criteria.get('role_level') and 'senior' in result.get('p.title', '').lower():
                scores[person_name] += 0.3
        
        # Score based on vector similarity
        for node in vector_results.source_nodes:
            person_name = node.metadata['name']
            similarity_score = node.score if hasattr(node, 'score') else 0.5
            scores[person_name] = scores.get(person_name, 0) + similarity_score
        
        # Sort by final score
        ranked_results = sorted(
            scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return ranked_results

    def _build_graph_query(self, criteria: Dict[str, str]) -> str:
        """Build Cypher query based on criteria"""
        query = """
        MATCH (p:Person)-[:WORKS_AT]->(c:Company)
        WHERE 1=1
        """
        
        if "company" in criteria:
            query += f"\nAND c.name CONTAINS '{criteria['company']}'"
        if "connected_after" in criteria:
            query += f"\nAND p.connected_on >= '{criteria['connected_after']}'"
        if "connected_before" in criteria:
            query += f"\nAND p.connected_on <= '{criteria['connected_before']}'"
            
        query += "\nRETURN p, c"
        
        return query

    def _build_vector_query(self, criteria: Dict[str, str]) -> str:
        """Build semantic search query based on criteria"""
        query = f"""
        Find professionals who are {criteria.get('role_level', '')} 
        in the {criteria.get('industry', '')} industry
        """
        if "skills" in criteria:
            query += f" with expertise in {criteria['skills']}"
            
        return query

    def get_connection_details(self, name: str) -> Dict:
        """Get detailed information about a specific connection"""
        # Get graph relationships
        graph_info = self.graph_store.query(f"""
            MATCH (p:Person {{name: '{name}'}})-[r]->(c:Company)
            RETURN {{
                person: p,
                company: c
            }} as result
        """)
        
        # Get similar profiles using vector search
        similar_profiles = self.vector_query_engine.query(
            f"Find professionals similar to {name}"
        ).source_nodes
        
        return {
            "graph_info": graph_info,
            "similar_profiles": [
                {
                    "name": node.metadata["name"],
                    "company": node.metadata.get("company", ""),
                    "similarity": node.score if hasattr(node, "score") else None
                }
                for node in similar_profiles[:5]
            ]
        } 