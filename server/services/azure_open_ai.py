"""Azure OpenAI services for language model and embeddings."""

"""Step 1: Import necessary modules"""
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, ChatOpenAI
from utils.consts import CONTEXT_LENGTH_LIMIT

"""Step 2: Define the Azure OpenAI services"""
# Define the function to get the Azure OpenAI variables
def get_azure_openai_variables():
    load_dotenv()
    AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT")
    AOAI_KEY = os.environ.get("AOAI_KEY")
    AOAI_API_VERSION = "2024-05-01-preview"
    AOAI_EMBEDDINGS = os.getenv("EMBEDDINGS_DEPLOYMENT_NAME")
    AOAI_COMPLETIONS = os.getenv("COMPLETIONS_DEPLOYMENT_NAME")

    return AOAI_ENDPOINT, AOAI_KEY, AOAI_API_VERSION, AOAI_EMBEDDINGS, AOAI_COMPLETIONS

# Get the DeepSeek variables
def get_deepseek_variables():
    load_dotenv()
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = "https://aimlapi.com/app/"  # or correct base
    return DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

def get_deepseek_llm():
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL = get_deepseek_variables()

    # Make sure streaming=False here
    llm = ChatOpenAI(
        temperature=0.3,
        openai_api_key=DEEPSEEK_API_KEY,
        base_url="https://api.aimlapi.com/v1",  # Replace with the correct base
        model_name="deepseek/deepseek-r1",
        max_tokens=(CONTEXT_LENGTH_LIMIT // 2),
        streaming=False,   # <--- ensure no streaming
        max_retries=3
    )
    return llm

# Define the function to get the Azure OpenAI language model
def get_azure_openai_llm():
    AOAI_ENDPOINT, AOAI_KEY, AOAI_API_VERSION, _, AOAI_COMPLETIONS = get_azure_openai_variables()

    llm = AzureChatOpenAI(
        temperature=0.3,
        azure_endpoint=AOAI_ENDPOINT,  
        openai_api_key=AOAI_KEY,
        openai_api_version=AOAI_API_VERSION,
        deployment_name=AOAI_COMPLETIONS,
        model_name="gpt-4o",  
        openai_api_type="azure",
        max_tokens=(CONTEXT_LENGTH_LIMIT // 2)
    )

    return llm


# Define the function to get the Azure OpenAI embeddings model
def get_azure_openai_embeddings():
    AOAI_ENDPOINT, AOAI_KEY, AOAI_API_VERSION, AOAI_EMBEDDINGS, _ = get_azure_openai_variables()

    embedding_model = AzureOpenAIEmbeddings(
        openai_api_key=AOAI_KEY,
        azure_endpoint=AOAI_ENDPOINT,
        openai_api_version=AOAI_API_VERSION,
        deployment=AOAI_EMBEDDINGS,
        model="text-embedding-3-small",  
        openai_api_type="azure",
        chunk_size=10
    )

    return embedding_model


