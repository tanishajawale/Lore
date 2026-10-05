from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict
import logging
import time
from .config import OPENAI_API_KEY, GROQ_API_KEY, MAX_TOKENS, TEMPERATURE, SUMMARY_BATCH_SIZE, MAX_WORDS_FOR_DIRECT_SUMMARY
from .vector_store import VectorStore

class RAGSystem:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.llm = None
        self.qa_chain = None
        self.summary_chain = None
        self._setup_llm()
    
    def _setup_llm(self):
        try:
            if not GROQ_API_KEY:
                logging.error("❌ GROQ_API_KEY not found in environment.")
                return
                
            self.llm = ChatGroq(
                temperature=TEMPERATURE,
                model_name="openai/gpt-oss-20b",
                max_tokens=2048,
                groq_api_key=GROQ_API_KEY
            )
            self._setup_chains()
        except Exception as e:
            logging.error(f"❌ Error initializing Groq LLM: {str(e)}")
    
    def _setup_chains(self):
        """Setup the LLM chains for Q&A and summarization."""
        # Q&A Chain
        qa_template = """
        You are a helpful assistant that answers questions based on the provided context.
        Use only the information from the context to answer the question.
        If the answer is not in the context, say "I don't have enough information to answer this question based on the provided documents."
        
        At the very end of your response, you MUST list the names of the specific documents you used to answer the question.
        Format it EXACTLY like this on a new line at the very end:
        SOURCES_USED: [Document Name 1, Document Name 2, etc]
        
        Chat History:
        {history}
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:"""
        
        qa_prompt = PromptTemplate(
            template=qa_template,
            input_variables=["context", "question", "history"]
        )
        self.qa_chain = qa_prompt | self.llm | StrOutputParser()
        
        # Summary Chain
        summary_template = """
        Please provide a comprehensive summary of the following text. 
        Focus on the main points, key concepts, and important details.
        Keep the summary clear and well-structured.
        
        Text:
        {text}
        
        Summary:"""
        
        summary_prompt = PromptTemplate(
            template=summary_template,
            input_variables=["text"]
        )
        self.summary_chain = summary_prompt | self.llm | StrOutputParser()
    
    def answer_question(self, question: str, history: List[Dict] = None, k: int = 10) -> Dict:
        """Answer a question using RAG and conversation history."""
        if not history:
            history = []
        if not self.llm or not self.qa_chain:
            return {
                "answer": "Language model not available. Please ensure your GROQ_API_KEY is added to api_config.env and the server is restarted.",
                "sources": [],
                "error": True
            }
        
        # Search for relevant documents
        search_results = self.vector_store.search(question, k=k)
        
        if not search_results:
            return {
                "answer": "I don't have any documents to search through. Please upload some PDFs first.",
                "sources": [],
                "error": False
            }
        
        # Prepare context and history strings
        context_parts = []
        sources = []
        
        for doc_text, metadata, score in search_results:
            context_parts.append(f"Document Name: {metadata['document']}\nContent: {doc_text}")
            sources.append({
                "document": metadata["document"],
                "chunk": metadata["chunk_index"],
                "relevance_score": score
            })
        
        context = "\n\n".join(context_parts)
        
        history_str = ""
        for msg in history[-4:]: # Only keep last 4 messages to save tokens
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"
        
        try:
            # Generate answer
            raw_response = self.qa_chain.invoke({
                "context": context, 
                "question": question,
                "history": history_str
            })
            
            # Parse out the actual sources used by the LLM
            answer = raw_response
            actual_sources = []
            unique_search_docs = set(s["document"] for s in sources)
            
            if "SOURCES_USED:" in raw_response:
                parts = raw_response.split("SOURCES_USED:")
                answer = parts[0].strip()
                cited_docs_str = parts[1].strip()
                
                # Verify the LLM cited a real document
                for doc in unique_search_docs:
                    if doc in cited_docs_str:
                        actual_sources.append({"document": doc})
            
            # Fallback if LLM failed to format correctly or didn't use any documents
            if not actual_sources:
                actual_sources = [{"document": doc} for doc in unique_search_docs]
            
            return {
                "answer": answer,
                "sources": actual_sources,
                "error": False
            }
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": sources,
                "error": True
            }
    
    def summarize_document(self, document_name: str) -> str:
        """Generate a summary for a specific document using chunked approach."""
        if not self.llm or not self.summary_chain:
            return "Language model not available. Please ensure your GROQ_API_KEY is added to api_config.env and the server is restarted."
        
        # Get all chunks for the document
        chunks = self.vector_store.get_document_chunks(document_name)
        
        if not chunks:
            return f"No content found for document: {document_name}"
        
        # If document is small enough, summarize directly
        full_text = "\n\n".join(chunks)
        if len(full_text.split()) < MAX_WORDS_FOR_DIRECT_SUMMARY:  # Rough token estimation
            try:
                summary = self.summary_chain.invoke({"text": full_text})
                return summary
            except Exception as e:
                return f"Error generating summary: {str(e)}"
        
        # For large documents, use chunked summarization
        try:
            return self._summarize_large_document(chunks, document_name)
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def _summarize_large_document(self, chunks: List[str], document_name: str) -> str:
        """Summarize a large document by processing chunks and creating a final summary."""
        # Process chunks in batches
        chunk_summaries = []
        batch_size = SUMMARY_BATCH_SIZE  # Process chunks in configurable batches
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        for i in range(0, len(chunks), batch_size):
            batch_num = i // batch_size + 1
            logging.info(f"Processing section {batch_num} of {total_batches}...")
            
            batch = chunks[i:i + batch_size]
            batch_text = "\n\n".join(batch)
            
            # Create a shorter prompt for chunk summarization
            chunk_prompt = f"""
            Please provide a concise summary of the following text section from "{document_name}".
            Focus on the main points and key information. Keep it brief but comprehensive.
            
            Text:
            {batch_text}
            
            Summary:"""
            
            try:
                chunk_summary_msg = self.llm.invoke(chunk_prompt)
                chunk_summary = chunk_summary_msg.content if hasattr(chunk_summary_msg, 'content') else str(chunk_summary_msg)
                chunk_summaries.append(chunk_summary)
            except Exception as e:
                # If chunk fails, add a placeholder
                chunk_summaries.append(f"[Section {batch_num} summary failed: {str(e)}]")
            
            # Sleep to prevent hitting Groq rate limits (429 Too Many Requests)
            time.sleep(2)
            
        logging.info("Creating final summary...")
        
        # Combine chunk summaries and create final summary
        combined_summaries = "\n\n".join(chunk_summaries)
        
        final_prompt = f"""
        Please create a comprehensive summary of the document "{document_name}" based on the following section summaries.
        Combine the information into a coherent, well-structured summary that covers all the main topics.
        
        Section Summaries:
        {combined_summaries}
        
        Final Document Summary:"""
        
        try:
            final_summary_msg = self.llm.invoke(final_prompt)
            final_summary = final_summary_msg.content if hasattr(final_summary_msg, 'content') else str(final_summary_msg)
            logging.info("Summary complete!")
            return final_summary
        except Exception as e:
            # Fallback: return the combined summaries
            logging.info("Summary complete!")
            return f"Summary of {document_name}:\n\n" + combined_summaries
    
    def summarize_all_documents(self) -> Dict[str, str]:
        """Generate summaries for all documents."""
        summaries = {}
        documents = self.vector_store.get_all_documents()
        
        for doc in documents:
            try:
                summaries[doc] = self.summarize_document(doc)
            except Exception as e:
                summaries[doc] = f"Error generating summary for {doc}: {str(e)}"
        
        return summaries
