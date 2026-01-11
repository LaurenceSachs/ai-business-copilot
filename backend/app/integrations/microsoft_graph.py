"""
Microsoft Graph API integration for Office 365 services.
Handles Outlook, To Do, Excel, Word, Teams, and OneDrive.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential
from app.core.config import settings


class MicrosoftGraphService:
    """Service for interacting with Microsoft Graph API."""

    def __init__(self, user_access_token: Optional[str] = None):
        """
        Initialize Graph API client.

        Args:
            user_access_token: Optional user-specific access token for delegated permissions
        """
        if user_access_token:
            # Use user's delegated token
            # For delegated access, we'd use a different credential type
            self.client = None  # Implement delegated auth flow
        else:
            # Use application credentials
            credential = ClientSecretCredential(
                tenant_id=settings.AZURE_TENANT_ID,
                client_id=settings.AZURE_CLIENT_ID,
                client_secret=settings.AZURE_CLIENT_SECRET,
            )
            self.client = GraphServiceClient(credential)

    async def get_emails(
        self,
        user_email: str,
        folder: str = "inbox",
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from a user's mailbox.

        Args:
            user_email: User's email address
            folder: Email folder (inbox, sent, etc.)
            limit: Maximum number of emails to fetch
            since: Only fetch emails since this date

        Returns:
            List of email dictionaries
        """
        # Build query
        query_params = {"$top": limit, "$orderby": "receivedDateTime desc"}
        if since:
            query_params["$filter"] = f"receivedDateTime ge {since.isoformat()}"

        messages = await self.client.users.by_user_id(user_email).mail_folders.by_mail_folder_id(folder).messages.get()

        emails = []
        for msg in messages.value:
            emails.append({
                "id": msg.id,
                "subject": msg.subject,
                "body": msg.body.content if msg.body else "",
                "from": msg.from_property.email_address.address if msg.from_property else None,
                "to": [recipient.email_address.address for recipient in (msg.to_recipients or [])],
                "received_date": msg.received_date_time,
                "has_attachments": msg.has_attachments,
                "web_link": msg.web_link,
            })

        return emails

    async def create_email_draft(
        self,
        user_email: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create an email draft (not sent).

        Args:
            user_email: User's email address
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML or plain text)
            cc: Optional CC recipients
            bcc: Optional BCC recipients

        Returns:
            Created draft details
        """
        draft_message = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body
            },
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        }

        if cc:
            draft_message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
        if bcc:
            draft_message["bccRecipients"] = [{"emailAddress": {"address": addr}} for addr in bcc]

        result = await self.client.users.by_user_id(user_email).messages.post(draft_message)

        return {
            "id": result.id,
            "subject": result.subject,
            "web_link": result.web_link,
        }

    async def get_calendar_events(
        self,
        user_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch calendar events.

        Args:
            user_email: User's email address
            start_date: Start date for events
            end_date: End date for events
            limit: Maximum number of events

        Returns:
            List of event dictionaries
        """
        query_params = {"$top": limit, "$orderby": "start/dateTime"}

        if start_date and end_date:
            query_params["$filter"] = f"start/dateTime ge '{start_date.isoformat()}' and end/dateTime le '{end_date.isoformat()}'"

        events = await self.client.users.by_user_id(user_email).calendar.events.get()

        return [
            {
                "id": event.id,
                "subject": event.subject,
                "body": event.body.content if event.body else "",
                "start": event.start.date_time,
                "end": event.end.date_time,
                "location": event.location.display_name if event.location else None,
                "attendees": [att.email_address.address for att in (event.attendees or [])],
                "web_link": event.web_link,
            }
            for event in events.value
        ]

    async def get_todo_tasks(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Fetch Microsoft To Do tasks.

        Args:
            user_email: User's email address

        Returns:
            List of task dictionaries
        """
        # Get all task lists first
        lists = await self.client.users.by_user_id(user_email).todo.lists.get()

        all_tasks = []
        for task_list in lists.value:
            tasks = await self.client.users.by_user_id(user_email).todo.lists.by_todo_task_list_id(task_list.id).tasks.get()

            for task in tasks.value:
                all_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "body": task.body.content if task.body else "",
                    "status": task.status,
                    "importance": task.importance,
                    "due_date": task.due_date_time.date_time if task.due_date_time else None,
                    "list_name": task_list.display_name,
                })

        return all_tasks

    async def create_todo_task(
        self,
        user_email: str,
        title: str,
        body: Optional[str] = None,
        due_date: Optional[datetime] = None,
        list_name: str = "Tasks"
    ) -> Dict[str, Any]:
        """
        Create a Microsoft To Do task.

        Args:
            user_email: User's email address
            title: Task title
            body: Task description
            due_date: Optional due date
            list_name: Name of the task list

        Returns:
            Created task details
        """
        # Find or create task list
        lists = await self.client.users.by_user_id(user_email).todo.lists.get()
        task_list = next((l for l in lists.value if l.display_name == list_name), None)

        if not task_list:
            # Create new list if not found
            task_list = await self.client.users.by_user_id(user_email).todo.lists.post({
                "displayName": list_name
            })

        # Create task
        task_data = {
            "title": title,
        }

        if body:
            task_data["body"] = {"content": body, "contentType": "text"}

        if due_date:
            task_data["dueDateTime"] = {
                "dateTime": due_date.isoformat(),
                "timeZone": "UTC"
            }

        result = await self.client.users.by_user_id(user_email).todo.lists.by_todo_task_list_id(task_list.id).tasks.post(task_data)

        return {
            "id": result.id,
            "title": result.title,
            "list_name": list_name,
        }

    async def search_onedrive_files(
        self,
        user_email: str,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search OneDrive files.

        Args:
            user_email: User's email address
            query: Search query
            limit: Maximum results

        Returns:
            List of file dictionaries
        """
        results = await self.client.users.by_user_id(user_email).drive.root.search(query).get()

        files = []
        for item in results.value[:limit]:
            files.append({
                "id": item.id,
                "name": item.name,
                "web_url": item.web_url,
                "created_date": item.created_date_time,
                "modified_date": item.last_modified_date_time,
                "size": item.size,
                "mime_type": item.file.mime_type if item.file else None,
            })

        return files
