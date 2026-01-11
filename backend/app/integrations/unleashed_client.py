"""
Unleashed Inventory integration (read-only).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import hmac
import hashlib
import requests
from app.core.config import settings


class UnleashedService:
    """Service for interacting with Unleashed Inventory API (read-only)."""

    BASE_URL = "https://api.unleashedsoftware.com"

    def __init__(self):
        """Initialize Unleashed API client."""
        self.api_id = settings.UNLEASHED_API_ID
        self.api_key = settings.UNLEASHED_API_KEY

    def _generate_signature(self, query_string: str) -> str:
        """
        Generate HMAC signature for Unleashed API request.

        Args:
            query_string: Query string for the request

        Returns:
            Base64-encoded HMAC signature
        """
        message = query_string.encode('utf-8')
        secret = self.api_key.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).digest()
        return signature.hex()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Unleashed API.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response data

        Raises:
            Exception: If request fails
        """
        query_string = ""
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        signature = self._generate_signature(query_string)

        headers = {
            "Accept": "application/json",
            "api-auth-id": self.api_id,
            "api-auth-signature": signature,
        }

        url = f"{self.BASE_URL}/{endpoint}"
        if query_string:
            url += f"?{query_string}"

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Unleashed API error: {response.status_code} - {response.text}")

        return response.json()

    def get_products(
        self,
        page: int = 1,
        page_size: int = 100,
        modified_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from Unleashed.

        Args:
            page: Page number
            page_size: Number of items per page
            modified_since: Only fetch products modified since this date

        Returns:
            List of product dictionaries
        """
        params = {
            "page": page,
            "pageSize": page_size,
        }

        if modified_since:
            params["modifiedSince"] = modified_since.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            data = self._make_request("Products", params)

            products = []
            for item in data.get("Items", []):
                products.append({
                    "id": item.get("Guid"),
                    "product_code": item.get("ProductCode"),
                    "product_description": item.get("ProductDescription"),
                    "barcode": item.get("Barcode"),
                    "available_qty": item.get("AvailableQty", 0),
                    "on_hand_qty": item.get("OnHandQty", 0),
                    "unit_of_measure": item.get("UnitOfMeasure"),
                    "default_sell_price": item.get("DefaultSellPrice", 0),
                    "obsolete": item.get("Obsolete", False),
                })

            return products

        except Exception as e:
            raise Exception(f"Failed to fetch products: {str(e)}")

    def get_stock_on_hand(
        self,
        product_code: Optional[str] = None,
        warehouse: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch stock on hand information.

        Args:
            product_code: Filter by product code
            warehouse: Filter by warehouse
            page: Page number
            page_size: Items per page

        Returns:
            List of stock records
        """
        params = {
            "page": page,
            "pageSize": page_size,
        }

        if product_code:
            params["productCode"] = product_code
        if warehouse:
            params["warehouse"] = warehouse

        try:
            data = self._make_request("StockOnHand", params)

            stock_items = []
            for item in data.get("Items", []):
                stock_items.append({
                    "product_code": item.get("ProductCode"),
                    "product_description": item.get("ProductDescription"),
                    "warehouse": item.get("Warehouse"),
                    "qty_on_hand": item.get("QtyOnHand", 0),
                    "qty_allocated": item.get("QtyAllocated", 0),
                    "qty_available": item.get("QtyAvailable", 0),
                })

            return stock_items

        except Exception as e:
            raise Exception(f"Failed to fetch stock on hand: {str(e)}")

    def get_sales_orders(
        self,
        page: int = 1,
        page_size: int = 100,
        modified_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch sales orders.

        Args:
            page: Page number
            page_size: Items per page
            modified_since: Only fetch orders modified since this date

        Returns:
            List of sales order dictionaries
        """
        params = {
            "page": page,
            "pageSize": page_size,
        }

        if modified_since:
            params["modifiedSince"] = modified_since.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            data = self._make_request("SalesOrders", params)

            orders = []
            for item in data.get("Items", []):
                orders.append({
                    "id": item.get("Guid"),
                    "order_number": item.get("OrderNumber"),
                    "customer": item.get("Customer", {}).get("CustomerName"),
                    "order_date": item.get("OrderDate"),
                    "required_date": item.get("RequiredDate"),
                    "order_status": item.get("OrderStatus"),
                    "sub_total": item.get("SubTotal", 0),
                    "total": item.get("Total", 0),
                })

            return orders

        except Exception as e:
            raise Exception(f"Failed to fetch sales orders: {str(e)}")

    def get_suppliers(
        self,
        page: int = 1,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch suppliers.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            List of supplier dictionaries
        """
        params = {
            "page": page,
            "pageSize": page_size,
        }

        try:
            data = self._make_request("Suppliers", params)

            suppliers = []
            for item in data.get("Items", []):
                suppliers.append({
                    "id": item.get("Guid"),
                    "supplier_code": item.get("SupplierCode"),
                    "supplier_name": item.get("SupplierName"),
                    "email": item.get("Email"),
                    "phone": item.get("PhoneNumber"),
                    "currency": item.get("Currency", {}).get("CurrencyCode"),
                })

            return suppliers

        except Exception as e:
            raise Exception(f"Failed to fetch suppliers: {str(e)}")

    def search_products(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for products by description or code.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching products
        """
        # Fetch products and filter client-side (Unleashed doesn't have full-text search)
        products = self.get_products(page_size=limit)

        matches = [
            prod for prod in products
            if query.lower() in (prod.get("product_description", "") or "").lower()
            or query.lower() in (prod.get("product_code", "") or "").lower()
        ]

        return matches[:limit]
