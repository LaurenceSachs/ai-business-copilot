"""
Xero Accounting integration (read-only).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from xero_python.api_client import ApiClient
from xero_python.api_client.configuration import Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi
from app.core.config import settings


class XeroService:
    """Service for interacting with Xero Accounting API (read-only)."""

    def __init__(self):
        """Initialize Xero API client."""
        # Configure OAuth2 token
        token = OAuth2Token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
        )
        token.refresh_token = settings.XERO_REFRESH_TOKEN

        # Create API client
        api_config = Configuration()
        api_config.access_token = token.access_token
        self.api_client = ApiClient(api_config)
        self.accounting_api = AccountingApi(self.api_client)
        self.tenant_id = settings.XERO_TENANT_ID

    def get_invoices(
        self,
        status: Optional[str] = None,
        since_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch invoices from Xero.

        Args:
            status: Filter by status (DRAFT, SUBMITTED, AUTHORISED, PAID, VOIDED)
            since_date: Only fetch invoices modified since this date
            limit: Maximum number of invoices

        Returns:
            List of invoice dictionaries
        """
        try:
            where_clause = None
            if status:
                where_clause = f'Status=="{status}"'

            if_modified_since = since_date

            invoices_response = self.accounting_api.get_invoices(
                self.tenant_id,
                if_modified_since=if_modified_since,
                where=where_clause,
                page=1,
            )

            invoices = []
            for inv in invoices_response.invoices[:limit]:
                invoices.append({
                    "id": inv.invoice_id,
                    "invoice_number": inv.invoice_number,
                    "type": inv.type,
                    "contact": inv.contact.name if inv.contact else None,
                    "status": inv.status,
                    "total": float(inv.total) if inv.total else 0,
                    "amount_due": float(inv.amount_due) if inv.amount_due else 0,
                    "date": inv.date,
                    "due_date": inv.due_date,
                    "reference": inv.reference,
                })

            return invoices

        except Exception as e:
            raise Exception(f"Xero API error: {str(e)}")

    def get_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch contacts from Xero.

        Args:
            limit: Maximum number of contacts

        Returns:
            List of contact dictionaries
        """
        try:
            contacts_response = self.accounting_api.get_contacts(
                self.tenant_id,
                page=1,
            )

            contacts = []
            for contact in contacts_response.contacts[:limit]:
                contacts.append({
                    "id": contact.contact_id,
                    "name": contact.name,
                    "email": contact.email_address,
                    "phone": contact.phones[0].phone_number if contact.phones else None,
                    "status": contact.contact_status,
                    "is_customer": contact.is_customer,
                    "is_supplier": contact.is_supplier,
                })

            return contacts

        except Exception as e:
            raise Exception(f"Xero API error: {str(e)}")

    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Fetch chart of accounts.

        Returns:
            List of account dictionaries
        """
        try:
            accounts_response = self.accounting_api.get_accounts(self.tenant_id)

            accounts = []
            for account in accounts_response.accounts:
                accounts.append({
                    "id": account.account_id,
                    "code": account.code,
                    "name": account.name,
                    "type": account.type,
                    "status": account.status,
                    "description": account.description,
                })

            return accounts

        except Exception as e:
            raise Exception(f"Xero API error: {str(e)}")

    def get_bank_transactions(
        self,
        since_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch bank transactions.

        Args:
            since_date: Only fetch transactions since this date
            limit: Maximum number of transactions

        Returns:
            List of transaction dictionaries
        """
        try:
            transactions_response = self.accounting_api.get_bank_transactions(
                self.tenant_id,
                if_modified_since=since_date,
                page=1,
            )

            transactions = []
            for txn in transactions_response.bank_transactions[:limit]:
                transactions.append({
                    "id": txn.bank_transaction_id,
                    "type": txn.type,
                    "contact": txn.contact.name if txn.contact else None,
                    "date": txn.date,
                    "status": txn.status,
                    "total": float(txn.total) if txn.total else 0,
                    "reference": txn.reference,
                })

            return transactions

        except Exception as e:
            raise Exception(f"Xero API error: {str(e)}")

    def get_profit_loss_report(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Get profit & loss report for a date range.

        Args:
            from_date: Start date for report
            to_date: End date for report

        Returns:
            Profit & loss report data
        """
        try:
            report = self.accounting_api.get_report_profit_and_loss(
                self.tenant_id,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
            )

            # Parse report data (structure varies)
            return {
                "report_name": "Profit and Loss",
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "data": report.to_dict(),
            }

        except Exception as e:
            raise Exception(f"Xero API error: {str(e)}")

    def search_transactions(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for transactions by reference or description.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching transactions
        """
        # Note: Xero doesn't have a full-text search API
        # We need to fetch and filter client-side
        transactions = self.get_bank_transactions(limit=limit)

        matches = [
            txn for txn in transactions
            if query.lower() in (txn.get("reference", "") or "").lower()
        ]

        return matches
