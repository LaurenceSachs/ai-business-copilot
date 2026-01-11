"""
HubSpot CRM integration for contacts, deals, notes, and tasks.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, ApiException
from app.core.config import settings


class HubSpotService:
    """Service for interacting with HubSpot CRM API."""

    def __init__(self):
        """Initialize HubSpot API client."""
        self.client = HubSpot(access_token=settings.HUBSPOT_ACCESS_TOKEN)

    def get_contacts(
        self,
        limit: int = 100,
        properties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch contacts from HubSpot.

        Args:
            limit: Maximum number of contacts to fetch
            properties: Specific properties to retrieve

        Returns:
            List of contact dictionaries
        """
        if properties is None:
            properties = ["firstname", "lastname", "email", "company", "phone", "createdate", "lastmodifieddate"]

        try:
            contacts_page = self.client.crm.contacts.basic_api.get_page(
                limit=limit,
                properties=properties,
            )

            contacts = []
            for contact in contacts_page.results:
                contacts.append({
                    "id": contact.id,
                    "properties": contact.properties,
                    "created_at": contact.created_at,
                    "updated_at": contact.updated_at,
                })

            return contacts

        except ApiException as e:
            raise Exception(f"HubSpot API error: {str(e)}")

    def search_contacts(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for contacts.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        try:
            search_request = {
                "query": query,
                "limit": limit,
                "properties": ["firstname", "lastname", "email", "company", "phone"],
            }

            results = self.client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )

            contacts = []
            for result in results.results:
                contacts.append({
                    "id": result.id,
                    "properties": result.properties,
                })

            return contacts

        except ApiException as e:
            raise Exception(f"HubSpot search error: {str(e)}")

    def get_deals(
        self,
        limit: int = 100,
        properties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch deals from HubSpot.

        Args:
            limit: Maximum number of deals to fetch
            properties: Specific properties to retrieve

        Returns:
            List of deal dictionaries
        """
        if properties is None:
            properties = ["dealname", "amount", "dealstage", "closedate", "createdate"]

        try:
            deals_page = self.client.crm.deals.basic_api.get_page(
                limit=limit,
                properties=properties,
            )

            deals = []
            for deal in deals_page.results:
                deals.append({
                    "id": deal.id,
                    "properties": deal.properties,
                    "created_at": deal.created_at,
                    "updated_at": deal.updated_at,
                })

            return deals

        except ApiException as e:
            raise Exception(f"HubSpot API error: {str(e)}")

    def create_note(
        self,
        note_body: str,
        associated_contacts: Optional[List[str]] = None,
        associated_deals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a note in HubSpot.

        Args:
            note_body: Content of the note
            associated_contacts: List of contact IDs to associate
            associated_deals: List of deal IDs to associate

        Returns:
            Created note details
        """
        try:
            note_input = {
                "properties": {
                    "hs_note_body": note_body,
                    "hs_timestamp": datetime.utcnow().isoformat(),
                }
            }

            # Create note
            note = self.client.crm.objects.notes.basic_api.create(
                simple_public_object_input_for_create=note_input
            )

            # Associate with contacts
            if associated_contacts:
                for contact_id in associated_contacts:
                    self.client.crm.objects.notes.associations_api.create(
                        note_id=note.id,
                        to_object_type="contacts",
                        to_object_id=contact_id,
                        association_type="note_to_contact",
                    )

            # Associate with deals
            if associated_deals:
                for deal_id in associated_deals:
                    self.client.crm.objects.notes.associations_api.create(
                        note_id=note.id,
                        to_object_type="deals",
                        to_object_id=deal_id,
                        association_type="note_to_deal",
                    )

            return {
                "id": note.id,
                "created_at": note.created_at,
            }

        except ApiException as e:
            raise Exception(f"Failed to create note: {str(e)}")

    def create_task(
        self,
        subject: str,
        body: Optional[str] = None,
        due_date: Optional[datetime] = None,
        assigned_to: Optional[str] = None,
        associated_contacts: Optional[List[str]] = None,
        associated_deals: Optional[List[str]] = None,
        priority: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Create a task in HubSpot.

        Args:
            subject: Task subject/title
            body: Task description
            due_date: Optional due date
            assigned_to: User ID to assign task to
            associated_contacts: List of contact IDs
            associated_deals: List of deal IDs
            priority: Task priority (HIGH, MEDIUM, LOW)

        Returns:
            Created task details
        """
        try:
            task_properties = {
                "hs_task_subject": subject,
                "hs_task_status": "NOT_STARTED",
                "hs_task_priority": priority,
            }

            if body:
                task_properties["hs_task_body"] = body

            if due_date:
                task_properties["hs_timestamp"] = due_date.isoformat()

            if assigned_to:
                task_properties["hubspot_owner_id"] = assigned_to

            task_input = {"properties": task_properties}

            # Create task
            task = self.client.crm.objects.tasks.basic_api.create(
                simple_public_object_input_for_create=task_input
            )

            # Associate with contacts
            if associated_contacts:
                for contact_id in associated_contacts:
                    self.client.crm.objects.tasks.associations_api.create(
                        task_id=task.id,
                        to_object_type="contacts",
                        to_object_id=contact_id,
                        association_type="task_to_contact",
                    )

            # Associate with deals
            if associated_deals:
                for deal_id in associated_deals:
                    self.client.crm.objects.tasks.associations_api.create(
                        task_id=task.id,
                        to_object_type="deals",
                        to_object_id=deal_id,
                        association_type="task_to_deal",
                    )

            return {
                "id": task.id,
                "created_at": task.created_at,
            }

        except ApiException as e:
            raise Exception(f"Failed to create task: {str(e)}")

    def get_notes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch notes from HubSpot.

        Args:
            limit: Maximum number of notes

        Returns:
            List of note dictionaries
        """
        try:
            notes_page = self.client.crm.objects.notes.basic_api.get_page(
                limit=limit,
                properties=["hs_note_body", "hs_timestamp"],
            )

            notes = []
            for note in notes_page.results:
                notes.append({
                    "id": note.id,
                    "body": note.properties.get("hs_note_body", ""),
                    "timestamp": note.properties.get("hs_timestamp"),
                    "created_at": note.created_at,
                })

            return notes

        except ApiException as e:
            raise Exception(f"HubSpot API error: {str(e)}")
