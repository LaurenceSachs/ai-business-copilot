"""
Query processing service using Claude AI for natural language understanding
and semantic search with pgvector.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import anthropic
from app.core.config import settings
from app.models.document import Document, DocumentSource
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User
from app.services.embedding_service import embedding_service


class QueryService:
    """Service for processing natural language queries with Claude AI."""

    def __init__(self, db: Session):
        """Initialize query service."""
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def process_query(
        self,
        user: User,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query.

        Args:
            user: User making the query
            query_text: Natural language query
            filters: Optional filters (system, date range, etc.)
            ip_address: User's IP address
            user_agent: User's agent string

        Returns:
            Query results with answer and citations
        """
        # Step 1: Generate embedding for semantic search
        query_embedding = embedding_service.generate_embedding(query_text)

        # Step 2: Perform hybrid search (semantic + keyword)
        documents = self._search_documents(query_embedding, query_text, filters, limit=20)

        # Step 3: Use Claude to analyze and answer
        answer = self._generate_answer_with_claude(query_text, documents)

        # Step 4: Extract citations
        citations = self._extract_citations(documents, answer)

        # Step 5: Log the query
        self._log_query(
            user=user,
            query_text=query_text,
            response_summary=answer.get("summary", ""),
            sources_used=[doc["id"] for doc in citations],
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "answer": answer.get("response", ""),
            "summary": answer.get("summary", ""),
            "citations": citations,
            "metadata": {
                "documents_searched": len(documents),
                "sources_used": len(citations),
            }
        }

    def _search_documents(
        self,
        query_embedding: List[float],
        query_text: str,
        filters: Optional[Dict[str, Any]],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid semantic + keyword search using pgvector.

        Args:
            query_embedding: Query embedding vector
            query_text: Original query text for keyword matching
            filters: Optional filters
            limit: Maximum documents to return

        Returns:
            List of matching documents
        """
        # Build base query for vector similarity search
        # Using pgvector's <=> operator for cosine distance
        query = text("""
            SELECT
                id,
                source,
                source_id,
                source_url,
                title,
                content,
                author,
                created_date,
                modified_date,
                metadata,
                1 - (embedding <=> :embedding) as similarity
            FROM documents
            WHERE 1=1
        """)

        # Add filters
        filter_conditions = []
        params = {"embedding": str(query_embedding), "limit": limit}

        if filters:
            if "source" in filters:
                filter_conditions.append("source = :source")
                params["source"] = filters["source"]

            if "start_date" in filters:
                filter_conditions.append("created_date >= :start_date")
                params["start_date"] = filters["start_date"]

            if "end_date" in filters:
                filter_conditions.append("created_date <= :end_date")
                params["end_date"] = filters["end_date"]

            if "author" in filters:
                filter_conditions.append("author = :author")
                params["author"] = filters["author"]

        # Combine query with filters
        if filter_conditions:
            query_str = str(query) + " AND " + " AND ".join(filter_conditions)
            query = text(query_str)

        # Add ordering and limit
        query = text(str(query) + " ORDER BY similarity DESC LIMIT :limit")

        # Execute query
        result = self.db.execute(query, params)
        rows = result.fetchall()

        documents = []
        for row in rows:
            documents.append({
                "id": row[0],
                "source": row[1],
                "source_id": row[2],
                "source_url": row[3],
                "title": row[4],
                "content": row[5][:1000] if row[5] else "",  # Truncate content
                "author": row[6],
                "created_date": row[7],
                "modified_date": row[8],
                "metadata": row[9],
                "similarity": row[10],
            })

        return documents

    def _generate_answer_with_claude(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Claude to generate an answer based on retrieved documents.

        Args:
            query: User's query
            documents: Retrieved documents

        Returns:
            AI-generated answer with summary
        """
        # Build context from documents
        context = "Here are the relevant documents from the business systems:\n\n"

        for i, doc in enumerate(documents, 1):
            context += f"[Document {i}]\n"
            context += f"Source: {doc['source']}\n"
            context += f"Title: {doc['title']}\n"
            context += f"Date: {doc.get('created_date', 'Unknown')}\n"
            context += f"Content: {doc['content']}\n"
            if doc.get('author'):
                context += f"Author: {doc['author']}\n"
            context += "\n---\n\n"

        # Build prompt for Claude
        prompt = f"""You are a business intelligence assistant helping users query their business data across multiple systems including Microsoft Office 365, Dropbox, Xero, Unleashed, and HubSpot.

User Query: {query}

{context}

Please provide a comprehensive answer to the user's query based on the documents above. In your response:
1. Directly answer the query
2. Cite specific documents using their document numbers (e.g., [Document 1])
3. If the documents don't contain enough information, clearly state what's missing
4. Be concise but thorough
5. Format your response in a clear, professional manner

Your response:"""

        try:
            # Call Claude API
            message = self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.MAX_TOKENS,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Generate a brief summary (first sentence or up to 150 chars)
            summary = response_text.split('.')[0][:150] + "..."

            return {
                "response": response_text,
                "summary": summary,
            }

        except Exception as e:
            return {
                "response": f"I encountered an error processing your query: {str(e)}",
                "summary": "Error processing query",
            }

    def _extract_citations(
        self,
        documents: List[Dict[str, Any]],
        answer: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract which documents were actually cited in the answer.

        Args:
            documents: All retrieved documents
            answer: Claude's answer

        Returns:
            List of cited documents
        """
        response_text = answer.get("response", "")
        citations = []

        for i, doc in enumerate(documents, 1):
            # Check if document is referenced in the response
            if f"[Document {i}]" in response_text or f"Document {i}" in response_text:
                citations.append({
                    "id": doc["id"],
                    "source": doc["source"],
                    "title": doc["title"],
                    "url": doc.get("source_url"),
                    "date": doc.get("created_date"),
                    "excerpt": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                })

        return citations

    def _log_query(
        self,
        user: User,
        query_text: str,
        response_summary: str,
        sources_used: List[int],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log query to audit log.

        Args:
            user: User who made the query
            query_text: Query text
            response_summary: Summary of response
            sources_used: List of document IDs used
            ip_address: User's IP
            user_agent: User's agent
        """
        audit_log = AuditLog(
            user_id=user.id,
            action=AuditAction.QUERY,
            description=f"User queried: {query_text[:100]}",
            query_text=query_text,
            response_summary=response_summary,
            sources_used=sources_used,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        self.db.commit()
