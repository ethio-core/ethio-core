#!/usr/bin/env python3
"""
Ethio-Core Audit Log Integrity Checker

This script verifies the integrity of the audit log hash chain
to detect any tampering or modifications.
"""

import hashlib
import json
import sys
import asyncio
from datetime import datetime
from typing import Optional, List
import asyncpg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ethio_core"


class IntegrityChecker:
    """Verifies the integrity of hash-linked audit logs."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to the database."""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=5)

    async def disconnect(self):
        """Disconnect from the database."""
        if self.pool:
            await self.pool.close()

    def compute_hash(self, record: dict, previous_hash: str) -> str:
        """Compute the hash of a record with the previous hash."""
        data = {
            "id": record["id"],
            "user_id": record["user_id"],
            "action": record["action"],
            "resource_type": record["resource_type"],
            "resource_id": record["resource_id"],
            "details": record["details"],
            "ip_address": record["ip_address"],
            "timestamp": record["timestamp"].isoformat() if record["timestamp"] else None,
            "previous_hash": previous_hash,
        }
        
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def verify_chain(self) -> dict:
        """Verify the entire audit log hash chain."""
        print("Starting integrity verification...")
        print("=" * 50)

        async with self.pool.acquire() as conn:
            # Get all audit logs ordered by timestamp
            rows = await conn.fetch("""
                SELECT id, user_id, action, resource_type, resource_id,
                       details, ip_address, timestamp, hash, previous_hash
                FROM audit_logs
                ORDER BY timestamp ASC
            """)

        if not rows:
            print("No audit logs found.")
            return {
                "status": "valid",
                "records_checked": 0,
                "invalid_records": [],
                "checked_at": datetime.utcnow().isoformat(),
            }

        total_records = len(rows)
        invalid_records: List[str] = []
        previous_hash = "GENESIS"

        for i, row in enumerate(rows):
            record = dict(row)
            
            # Verify the hash
            expected_hash = self.compute_hash(record, previous_hash)
            stored_hash = record["hash"]

            if expected_hash != stored_hash:
                invalid_records.append(str(record["id"]))
                print(f"[INVALID] Record {record['id']}: Hash mismatch")
                print(f"  Expected: {expected_hash}")
                print(f"  Stored:   {stored_hash}")
            
            # Update previous hash for next iteration
            previous_hash = stored_hash

            # Progress update
            if (i + 1) % 1000 == 0 or (i + 1) == total_records:
                print(f"Verified {i + 1}/{total_records} records...")

        # Generate report
        status = "valid" if len(invalid_records) == 0 else "invalid"
        
        print()
        print("=" * 50)
        print("INTEGRITY CHECK REPORT")
        print("=" * 50)
        print(f"Status: {status.upper()}")
        print(f"Records Checked: {total_records}")
        print(f"Invalid Records: {len(invalid_records)}")
        
        if invalid_records:
            print(f"Invalid Record IDs: {', '.join(invalid_records[:10])}")
            if len(invalid_records) > 10:
                print(f"  ... and {len(invalid_records) - 10} more")

        return {
            "status": status,
            "records_checked": total_records,
            "invalid_records": invalid_records,
            "checked_at": datetime.utcnow().isoformat(),
        }

    async def repair_chain(self, start_from: Optional[str] = None):
        """Repair the hash chain starting from a specific record."""
        print("Starting hash chain repair...")
        print("⚠️  This will recalculate hashes from the specified point.")
        
        async with self.pool.acquire() as conn:
            if start_from:
                rows = await conn.fetch("""
                    SELECT id, user_id, action, resource_type, resource_id,
                           details, ip_address, timestamp, hash, previous_hash
                    FROM audit_logs
                    WHERE timestamp >= (SELECT timestamp FROM audit_logs WHERE id = $1)
                    ORDER BY timestamp ASC
                """, start_from)
                
                # Get previous hash
                prev_row = await conn.fetchrow("""
                    SELECT hash FROM audit_logs
                    WHERE timestamp < (SELECT timestamp FROM audit_logs WHERE id = $1)
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, start_from)
                previous_hash = prev_row["hash"] if prev_row else "GENESIS"
            else:
                rows = await conn.fetch("""
                    SELECT id, user_id, action, resource_type, resource_id,
                           details, ip_address, timestamp, hash, previous_hash
                    FROM audit_logs
                    ORDER BY timestamp ASC
                """)
                previous_hash = "GENESIS"

            for row in rows:
                record = dict(row)
                new_hash = self.compute_hash(record, previous_hash)
                
                await conn.execute("""
                    UPDATE audit_logs
                    SET hash = $1, previous_hash = $2
                    WHERE id = $3
                """, new_hash, previous_hash, record["id"])
                
                previous_hash = new_hash

        print(f"Repaired {len(rows)} records.")


async def main():
    """Main entry point."""
    checker = IntegrityChecker(DATABASE_URL)
    
    try:
        await checker.connect()
        
        if len(sys.argv) > 1 and sys.argv[1] == "--repair":
            start_from = sys.argv[2] if len(sys.argv) > 2 else None
            await checker.repair_chain(start_from)
        else:
            result = await checker.verify_chain()
            
            # Exit with error code if invalid
            if result["status"] == "invalid":
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await checker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
