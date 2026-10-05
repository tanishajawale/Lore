import PyPDF2
import logging
from typing import List, Dict
import io
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import CHUNK_SIZE, CHUNK_OVERLAP

class PDFProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from a PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def process_pdfs(self, uploaded_files: List) -> Dict[str, List[str]]:
        """Process multiple PDF files and return chunked text."""
        processed_docs = {}
        
        for uploaded_file in uploaded_files:
            file_obj = getattr(uploaded_file, "file", uploaded_file)
            if getattr(uploaded_file, "content_type", getattr(uploaded_file, "type", "")) == "application/pdf":
                # Extract text
                text = self.extract_text_from_pdf(file_obj)
                
                if text:
                    # Split into chunks
                    chunks = self.text_splitter.split_text(text)
                    processed_docs[getattr(uploaded_file, "filename", getattr(uploaded_file, "name", "unknown.pdf"))] = chunks
                    logging.info(f"✅ Processed {getattr(uploaded_file, 'filename', getattr(uploaded_file, 'name', 'unknown.pdf'))}: {len(chunks)} chunks")
                else:
                    logging.warning(f"⚠️ No text extracted from {getattr(uploaded_file, 'filename', getattr(uploaded_file, 'name', 'unknown.pdf'))}")
            else:
                logging.error(f"❌ {getattr(uploaded_file, 'filename', getattr(uploaded_file, 'name', 'unknown.pdf'))} is not a PDF file")
        
        return processed_docs
    
    def get_document_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a simple summary of the document."""
        if len(text) <= max_length:
            return text
        
        # Simple extractive summary - take first and last parts
        words = text.split()
        if len(words) <= max_length:
            return text
        
        # Take first 40% and last 40% of the text
        first_part = words[:max_length//2]
        last_part = words[-(max_length//2):]
        
        return " ".join(first_part) + " ... " + " ".join(last_part)
