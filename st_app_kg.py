import streamlit as st
from ingest import LinkedInDataIngester
from analyzer import LinkedInAnalyzer
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
import pandas as pd
from datetime import datetime

def setup_llamaindex():
    """Configure LlamaIndex settings"""
    Settings.llm = OpenAI(model="gpt-4", api_key=st.secrets["OPENAI_API_KEY"])
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=st.secrets["OPENAI_API_KEY"]
    )

def initialize_analyzer(csv_file):
    """Initialize the LinkedIn data analyzer"""
    ingester = LinkedInDataIngester(
        neo4j_url=st.secrets["NEO4J_URL"],
        neo4j_username=st.secrets["NEO4J_USERNAME"],
        neo4j_password=st.secrets["NEO4J_PASSWORD"]
    )
    
    documents = ingester.load_linkedin_data(csv_file)
    ingester.create_knowledge_graph(documents)
    vector_index = ingester.build_indexes(documents)
    
    return LinkedInAnalyzer(vector_index, ingester.graph_store)

def main():
    st.title("LinkedIn Network Analyzer")
    st.sidebar.header("Analysis Options")
    
    # File upload
    uploaded_file = st.file_uploader("Upload your LinkedIn connections CSV", type="csv")
    
    if uploaded_file is not None:
        try:
            # Initialize the analyzer
            setup_llamaindex()
            analyzer = initialize_analyzer(uploaded_file)
            
            # Analysis type selection
            analysis_type = st.sidebar.selectbox(
                "Select Analysis Type",
                ["Company Analysis", "Connection Timeline", "Profile Search"]
            )
            
            if analysis_type == "Company Analysis":
                st.subheader("Company Analysis")
                company_name = st.text_input("Enter Company Name")
                
                if company_name:
                    connections = analyzer.find_interesting_connections({
                        "company": company_name
                    })
                    
                    if connections:
                        st.write(f"### Connections at {company_name}")
                        for name, score in connections[:10]:
                            st.write(f"- {name} (Relevance: {score:.2f})")
                            
                            # Show detailed profile on click
                            if st.button(f"View Details: {name}"):
                                details = analyzer.get_connection_details(name)
                                st.write("#### Profile Details")
                                if details["graph_info"]:
                                    person_info = details["graph_info"][0]["person"]
                                    company_info = details["graph_info"][0]["company"]
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write("**Contact Info**")
                                        st.write(f"Email: {person_info.get('email', 'Not available')}")
                                        st.write(f"LinkedIn: {person_info.get('linkedin_url', 'Not available')}")
                                    
                                    with col2:
                                        st.write("**Professional Info**")
                                        st.write(f"Company: {company_info['name']}")
                                        st.write(f"Connected On: {person_info.get('connected_on', 'Not available')}")
                                    
                                    st.write("**Similar Profiles**")
                                    for profile in details["similar_profiles"]:
                                        st.write(f"- {profile['name']} at {profile['company']}")
                    else:
                        st.write("No connections found at this company.")
            
            elif analysis_type == "Connection Timeline":
                st.subheader("Connection Timeline")
                
                # Date range selection
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date")
                with col2:
                    end_date = st.date_input("End Date")
                
                if start_date and end_date:
                    connections = analyzer.find_interesting_connections({
                        "connected_after": start_date.strftime("%Y-%m-%d"),
                        "connected_before": end_date.strftime("%Y-%m-%d")
                    })
                    
                    if connections:
                        st.write(f"### Connections between {start_date} and {end_date}")
                        for name, score in connections[:10]:
                            st.write(f"- {name} (Connected on: {score:.2f})")
                    else:
                        st.write("No connections found in this date range.")
            
            elif analysis_type == "Profile Search":
                st.subheader("Profile Search")
                search_name = st.text_input("Enter Connection Name")
                
                if search_name:
                    details = analyzer.get_connection_details(search_name)
                    
                    if details["graph_info"]:
                        person_info = details["graph_info"][0]["person"]
                        company_info = details["graph_info"][0]["company"]
                        
                        st.write("### Profile Information")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Contact Information**")
                            st.write(f"- Email: {person_info.get('email', 'Not available')}")
                            st.write(f"- LinkedIn: {person_info.get('linkedin_url', 'Not available')}")
                        
                        with col2:
                            st.write("**Professional Information**")
                            st.write(f"- Company: {company_info['name']}")
                            st.write(f"- Connected On: {person_info.get('connected_on', 'Not available')}")
                        
                        st.write("### Similar Profiles")
                        for profile in details["similar_profiles"]:
                            st.write(f"- {profile['name']} at {profile['company']}")
                    else:
                        st.write("Profile not found.")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    
    else:
        st.info("""
        ### How to get your LinkedIn connections CSV:
        1. Go to LinkedIn
        2. Click on 'Me' → 'Settings & Privacy'
        3. Go to 'Data privacy' → 'Get a copy of your data'
        4. Select 'Connections' and request the archive
        5. Download and upload the CSV file here
        """)

if __name__ == "__main__":
    main() 