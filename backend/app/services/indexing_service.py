"""
Indexing service for ingesting and indexing content from all integrated systems.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import Document, DocumentSource
from app.services.embedding_service import embedding_service
from app.integrations.microsoft_graph import MicrosoftGraphService
from app.integrations.dropbox_client import DropboxService
from app.integrations.hubspot_client import HubSpotService
from app.integrations.xero_client import XeroService
from app.integrations.unleashed_client import UnleashedService


class IndexingService:
    """Service for indexing content from all business systems."""

    def __init__(self, db: Session):
        """Initialize indexing service with database session."""
        self.db = db
        self.ms_graph = MicrosoftGraphService()
        self.dropbox = DropboxService()
        self.hubspot = HubSpotService()
        self.xero = XeroService()
        self.unleashed = UnleashedService()

    def index_all_sources(self, incremental: bool = False) -> Dict[str, int]:
        """
        Index all configured data sources.

        Args:
            incremental: If True, only index new/modified content since last sync

        Returns:
            Dictionary with counts of indexed items per source
        """
        results = {}

        # Determine cutoff date for incremental indexing
        cutoff_date = None
        if incremental:
            cutoff_date = datetime.utcnow() - timedelta(days=7)

        # Index each source
        results["outlook_emails"] = self.index_outlook_emails(since=cutoff_date)
        results["dropbox_files"] = self.index_dropbox_files(since=cutoff_date)
        results["hubspot_contacts"] = self.index_hubspot_contacts()
        results["hubspot_deals"] = self.index_hubspot_deals()
        results["hubspot_notes"] = self.index_hubspot_notes()
        results["xero_invoices"] = self.index_xero_invoices(since=cutoff_date)
        results["xero_contacts"] = self.index_xero_contacts()
        results["unleashed_products"] = self.index_unleashed_products(since=cutoff_date)
        results["unleashed_sales_orders"] = self.index_unleashed_sales_orders(since=cutoff_date)

        return results

    def index_outlook_emails(self, since: Optional[datetime] = None, user_email: str = "me") -> int:
        """Index emails from Outlook."""
        try:
            emails = self.ms_graph.get_emails(user_email, limit=500, since=since)

            indexed_count = 0
            for email in emails:
                # Check if already indexed
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.OUTLOOK_EMAIL,
                    Document.source_id == email["id"]
                ).first()

                # Prepare content for embedding
                content = f"{email['subject']}\n\n{email['body']}"
                embedding = embedding_service.generate_embedding(content[:5000])  # Limit content length

                if existing:
                    # Update existing document
                    existing.content = email["body"]
                    existing.title = email["subject"]
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = {
                        "from": email["from"],
                        "to": email["to"],
                        "has_attachments": email["has_attachments"],
                    }
                else:
                    # Create new document
                    doc = Document(
                        source=DocumentSource.OUTLOOK_EMAIL,
                        source_id=email["id"],
                        source_url=email["web_link"],
                        title=email["subject"],
                        content=email["body"],
                        embedding=embedding,
                        author=email["from"],
                        created_date=email["received_date"],
                        metadata={
                            "from": email["from"],
                            "to": email["to"],
                            "has_attachments": email["has_attachments"],
                        }
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Outlook emails: {str(e)}")

    def index_dropbox_files(self, since: Optional[datetime] = None) -> int:
        """Index files from Dropbox."""
        try:
            files = self.dropbox.list_files(recursive=True, limit=1000)

            indexed_count = 0
            for file in files:
                # Skip if not modified since cutoff
                if since and file["modified_date"] < since:
                    continue

                # Check if already indexed
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.DROPBOX,
                    Document.source_id == file["id"]
                ).first()

                # For text files, download content; otherwise just index metadata
                content = ""
                file_extension = file["name"].split(".")[-1].lower()
                if file_extension in ["txt", "md", "csv", "json", "xml", "py", "js", "html", "css"]:
                    try:
                        content = self.dropbox.download_file_as_text(file["path"])[:10000]  # Limit size
                    except:
                        pass  # Skip if can't decode as text

                # Generate embedding
                embed_text = f"{file['name']}\n{content}" if content else file['name']
                embedding = embedding_service.generate_embedding(embed_text[:5000])

                if existing:
                    # Update if content hash changed
                    if existing.metadata.get("content_hash") != file["content_hash"]:
                        existing.content = content
                        existing.embedding = embedding
                        existing.modified_date = file["modified_date"]
                        existing.last_synced_at = datetime.utcnow()
                        existing.metadata["content_hash"] = file["content_hash"]
                else:
                    # Create new document
                    doc = Document(
                        source=DocumentSource.DROPBOX,
                        source_id=file["id"],
                        source_url=file["path"],  # Will be converted to shared link when needed
                        title=file["name"],
                        content=content,
                        embedding=embedding,
                        created_date=file["modified_date"],
                        modified_date=file["modified_date"],
                        metadata={
                            "path": file["path"],
                            "size": file["size"],
                            "content_hash": file["content_hash"],
                        }
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Dropbox files: {str(e)}")

    def index_hubspot_contacts(self) -> int:
        """Index contacts from HubSpot."""
        try:
            contacts = self.hubspot.get_contacts(limit=500)

            indexed_count = 0
            for contact in contacts:
                props = contact["properties"]
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.HUBSPOT_CONTACT,
                    Document.source_id == contact["id"]
                ).first()

                # Build searchable content
                content = f"Contact: {props.get('firstname', '')} {props.get('lastname', '')}\n"
                content += f"Email: {props.get('email', '')}\n"
                content += f"Company: {props.get('company', '')}\n"
                content += f"Phone: {props.get('phone', '')}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = props
                else:
                    doc = Document(
                        source=DocumentSource.HUBSPOT_CONTACT,
                        source_id=contact["id"],
                        title=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                        content=content,
                        embedding=embedding,
                        created_date=contact.get("created_at"),
                        modified_date=contact.get("updated_at"),
                        metadata=props
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index HubSpot contacts: {str(e)}")

    def index_hubspot_deals(self) -> int:
        """Index deals from HubSpot."""
        try:
            deals = self.hubspot.get_deals(limit=500)
            indexed_count = 0

            for deal in deals:
                props = deal["properties"]
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.HUBSPOT_DEAL,
                    Document.source_id == deal["id"]
                ).first()

                content = f"Deal: {props.get('dealname', '')}\n"
                content += f"Amount: {props.get('amount', '')}\n"
                content += f"Stage: {props.get('dealstage', '')}\n"
                content += f"Close Date: {props.get('closedate', '')}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = props
                else:
                    doc = Document(
                        source=DocumentSource.HUBSPOT_DEAL,
                        source_id=deal["id"],
                        title=props.get("dealname", "Untitled Deal"),
                        content=content,
                        embedding=embedding,
                        created_date=deal.get("created_at"),
                        modified_date=deal.get("updated_at"),
                        metadata=props
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index HubSpot deals: {str(e)}")

    def index_hubspot_notes(self) -> int:
        """Index notes from HubSpot."""
        try:
            notes = self.hubspot.get_notes(limit=500)
            indexed_count = 0

            for note in notes:
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.HUBSPOT_NOTE,
                    Document.source_id == note["id"]
                ).first()

                content = note["body"]
                embedding = embedding_service.generate_embedding(content[:5000])

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                else:
                    doc = Document(
                        source=DocumentSource.HUBSPOT_NOTE,
                        source_id=note["id"],
                        title=f"Note from {note.get('timestamp', 'Unknown')}",
                        content=content,
                        embedding=embedding,
                        created_date=note.get("created_at"),
                        metadata={"timestamp": note.get("timestamp")}
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index HubSpot notes: {str(e)}")

    def index_xero_invoices(self, since: Optional[datetime] = None) -> int:
        """Index invoices from Xero."""
        try:
            invoices = self.xero.get_invoices(since_date=since, limit=500)
            indexed_count = 0

            for invoice in invoices:
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.XERO,
                    Document.source_id == invoice["id"]
                ).first()

                content = f"Invoice #{invoice['invoice_number']}\n"
                content += f"Contact: {invoice['contact']}\n"
                content += f"Status: {invoice['status']}\n"
                content += f"Total: ${invoice['total']}\n"
                content += f"Amount Due: ${invoice['amount_due']}\n"
                content += f"Due Date: {invoice['due_date']}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = invoice
                else:
                    doc = Document(
                        source=DocumentSource.XERO,
                        source_id=invoice["id"],
                        title=f"Invoice {invoice['invoice_number']}",
                        content=content,
                        embedding=embedding,
                        created_date=invoice["date"],
                        metadata=invoice
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Xero invoices: {str(e)}")

    def index_xero_contacts(self) -> int:
        """Index contacts from Xero."""
        try:
            contacts = self.xero.get_contacts(limit=500)
            indexed_count = 0

            for contact in contacts:
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.XERO,
                    Document.source_id == contact["id"]
                ).first()

                content = f"Contact: {contact['name']}\n"
                content += f"Email: {contact.get('email', '')}\n"
                content += f"Phone: {contact.get('phone', '')}\n"
                content += f"Customer: {'Yes' if contact.get('is_customer') else 'No'}\n"
                content += f"Supplier: {'Yes' if contact.get('is_supplier') else 'No'}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                else:
                    doc = Document(
                        source=DocumentSource.XERO,
                        source_id=contact["id"],
                        title=contact["name"],
                        content=content,
                        embedding=embedding,
                        metadata=contact
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Xero contacts: {str(e)}")

    def index_unleashed_products(self, since: Optional[datetime] = None) -> int:
        """Index products from Unleashed."""
        try:
            products = self.unleashed.get_products(page_size=500, modified_since=since)
            indexed_count = 0

            for product in products:
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.UNLEASHED,
                    Document.source_id == product["id"]
                ).first()

                content = f"Product: {product['product_code']} - {product['product_description']}\n"
                content += f"Barcode: {product.get('barcode', '')}\n"
                content += f"Available Qty: {product['available_qty']}\n"
                content += f"On Hand Qty: {product['on_hand_qty']}\n"
                content += f"Unit of Measure: {product['unit_of_measure']}\n"
                content += f"Sell Price: ${product['default_sell_price']}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = product
                else:
                    doc = Document(
                        source=DocumentSource.UNLEASHED,
                        source_id=product["id"],
                        title=f"{product['product_code']} - {product['product_description']}",
                        content=content,
                        embedding=embedding,
                        metadata=product
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Unleashed products: {str(e)}")

    def index_unleashed_sales_orders(self, since: Optional[datetime] = None) -> int:
        """Index sales orders from Unleashed."""
        try:
            orders = self.unleashed.get_sales_orders(page_size=500, modified_since=since)
            indexed_count = 0

            for order in orders:
                existing = self.db.query(Document).filter(
                    Document.source == DocumentSource.UNLEASHED,
                    Document.source_id == order["id"]
                ).first()

                content = f"Sales Order: {order['order_number']}\n"
                content += f"Customer: {order['customer']}\n"
                content += f"Order Date: {order['order_date']}\n"
                content += f"Required Date: {order.get('required_date', '')}\n"
                content += f"Status: {order['order_status']}\n"
                content += f"Total: ${order['total']}"

                embedding = embedding_service.generate_embedding(content)

                if existing:
                    existing.content = content
                    existing.embedding = embedding
                    existing.last_synced_at = datetime.utcnow()
                    existing.metadata = order
                else:
                    doc = Document(
                        source=DocumentSource.UNLEASHED,
                        source_id=order["id"],
                        title=f"Order {order['order_number']}",
                        content=content,
                        embedding=embedding,
                        metadata=order
                    )
                    self.db.add(doc)

                indexed_count += 1

            self.db.commit()
            return indexed_count

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to index Unleashed sales orders: {str(e)}")
