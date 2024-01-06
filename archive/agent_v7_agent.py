from langchain.agents import Tool
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings.openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain.agents import initialize_agent
from langchain.tools import ShellTool
from langchain.tools import DuckDuckGoSearchRun
import json
import sys
import warnings

def main():
    # Read config from json
    if len(sys.argv) > 1:
        # Iterate over the arguments (excluding the script name)
        for i, arg in enumerate(sys.argv[1:]):
            print(f"Argument {i+1}: {arg}")
        config_filename = sys.argv[1]
    else:
        config_filename = 'config.json'
    with open(config_filename, 'r') as f:
        config = json.load(f)

    class DocumentInput(BaseModel):
        question: str = Field()
    
    llm = ChatOpenAI(
        openai_api_key=config['openai']['api_key'],
        model=config['openai']['model'],
        temperature=config['openai']['temperature']
        )
    
    # Retrieval
    context_path = config['context']['path']
    loader = DirectoryLoader(context_path, glob="*", loader_cls=TextLoader)
    docs = loader.load()
    embeddings = OpenAIEmbeddings(openai_api_key=config['openai']['api_key'])
    text_splitter = RecursiveCharacterTextSplitter()
    documents = text_splitter.split_documents(docs)
    print(f"Additional documents in context: {len(documents)}")
    vector = DocArrayInMemorySearch.from_documents(documents, embeddings)
    retriever = vector.as_retriever()

    # Tools initialization
    tools = []
    # Wrap retrievers in a Tool
    tools.append(
        Tool(
            args_schema=DocumentInput,
            name='Additional context',
            description=f"Additional context that has been provided by user",
            func=RetrievalQA.from_chain_type(llm=llm, retriever=retriever),
        )
    )
    # Add ShellTool
    tools.append(ShellTool())
    # Add DuckDuckGoSearchRun
    tools.append(DuckDuckGoSearchRun())

    # Agent initialization
    # https://api.python.langchain.com/en/latest/agents/langchain.agents.agent_types.AgentType.html
    agent_type = 'chat-conversational-react-description'
    agent = initialize_agent(tools, llm, agent=agent_type, verbose=True, handle_parsing_errors=True)

    # Disable warnings
    warnings.filterwarnings('ignore', category=UserWarning)

    # Chat history
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input != 'exit' or user_input != 'quit':
            break
        agent.run(input=user_input, chat_history=chat_history)


if __name__ == '__main__':
    main()
