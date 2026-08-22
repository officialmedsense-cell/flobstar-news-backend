"""
High-Speed Supabase REST Client
Provides fast, firewall-immune queries over HTTPS port 443 (REST API)
Replaces raw TCP port 5432 to guarantee zero connection timeouts.
"""

import httpx
from typing import Optional, Dict, Any, List
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class SupabaseClient:
    """Async Supabase REST client using httpx."""

    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def get(self, table: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query a table via REST."""
        url = f"{self.base_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers, params=params or {})
                if resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else [data]
                logger.warning(f"Supabase GET {table} returned {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Supabase GET {table} exception: {e}")
            return []

    async def get_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single record by ID."""
        url = f"{self.base_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers, params={"id": f"eq.{record_id}", "limit": "1"})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                return None
        except Exception as e:
            logger.error(f"Supabase GET {table} by ID exception: {e}")
            return None

    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert a single record into a table."""
        url = f"{self.base_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self.headers, json=data)
                if resp.status_code in (200, 201):
                    res = resp.json()
                    return res[0] if isinstance(res, list) and len(res) > 0 else res
                logger.error(f"Supabase INSERT {table} failed {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Supabase INSERT {table} exception: {e}")
            return None

    async def update(self, table: str, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record by ID."""
        url = f"{self.base_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.patch(url, headers=self.headers, params={"id": f"eq.{record_id}"}, json=data)
                if resp.status_code in (200, 204):
                    res = resp.json() if resp.status_code == 200 else {"id": record_id, **data}
                    return res[0] if isinstance(res, list) and len(res) > 0 else res
                logger.error(f"Supabase UPDATE {table} failed {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Supabase UPDATE {table} exception: {e}")
            return None

    async def delete(self, table: str, record_id: str) -> bool:
        """Delete a record by ID."""
        url = f"{self.base_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=self.headers, params={"id": f"eq.{record_id}"})
                return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Supabase DELETE {table} exception: {e}")
            return False


# Global REST client instance
supabase_client = SupabaseClient()
