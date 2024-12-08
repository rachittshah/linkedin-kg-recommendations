from ingest import LinkedInDataIngester
from analyzer import LinkedInAnalyzer
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

def setup_llamaindex():
    """Configure LlamaIndex settings"""
    Settings.llm = OpenAI(model="gpt-4")
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

def analyze_network():
    """Analyze the LinkedIn network for insights"""
    # Initialize components
    ingester = LinkedInDataIngester(
        neo4j_url="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="password"
    )
    
    # Load and process data
    documents = ingester.load_linkedin_data("linkedin_connections.csv")
    ingester.create_knowledge_graph(documents)
    vector_index = ingester.build_indexes(documents)
    
    # Initialize analyzer
    analyzer = LinkedInAnalyzer(vector_index, ingester.graph_store)
    
    # Example analyses
    
    # 1. Find recent connections at specific companies
    recent_tech_connections = analyzer.find_interesting_connections({
        "company": "Google",
        "connected_after": "2023-01-01"
    })
    print("\nRecent Tech Company Connections:", recent_tech_connections[:5])
    
    # 2. Find connections by company
    company_connections = analyzer.find_interesting_connections({
        "company": "Microsoft"
    })
    print("\nMicrosoft Connections:", company_connections[:5])
    
    # 3. Get detailed profile analysis
    if recent_tech_connections:
        top_connection = recent_tech_connections[0][0]  # Get name of top connection
        details = analyzer.get_connection_details(top_connection)
        print(f"\nDetailed Profile for {top_connection}:", details)

def main():
    # Setup LlamaIndex
    setup_llamaindex()
    
    try:
        # Run network analysis
        analyze_network()
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main() 