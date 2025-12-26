import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(__file__).parent.parent / "enhancer.db"


class RecoveryManager:
    
    def __init__(self, auto_recover: bool = True) -> None:
        self.auto_recover = auto_recover
    
    def scan_for_issues(self) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        issues: List[Dict] = []
        
        cursor.execute("""
            SELECT id, tweak_id, applied_at, status
            FROM tweak_history
            WHERE status = 'pending'
        """)
        
        for row in cursor.fetchall():
            history_id, tweak_id, applied_at, status = row
            issues.append({
                "type": "stuck_pending",
                "history_id": history_id,
                "tweak_id": tweak_id,
                "applied_at": applied_at,
                "reason": "Operation never started - likely process crash before apply"
            })
        
        timeout_threshold = datetime.now() - timedelta(minutes=5)
        cursor.execute("""
            SELECT id, tweak_id, applied_at, status
            FROM tweak_history
            WHERE status = 'applying' 
            AND applied_at < ?
        """, (timeout_threshold,))
        
        for row in cursor.fetchall():
            history_id, tweak_id, applied_at, status = row
            issues.append({
                "type": "stuck_applying",
                "history_id": history_id,
                "tweak_id": tweak_id,
                "applied_at": applied_at,
                "reason": "Operation timed out - possible system hang during apply"
            })
        
        conn.close()
        return issues
    
    def recover_all(self, manager) -> Dict:
        issues = self.scan_for_issues()
        
        if not issues:
            return {
                "issues_found": 0,
                "recovered": 0,
                "failed": 0,
                "details": []
            }
        
        results = {
            "issues_found": len(issues),
            "recovered": 0,
            "failed": 0,
            "details": []
        }
        
        for issue in issues:
            print(f"\n[RECOVERY] Found issue: {issue['tweak_id']} ({issue['type']})")
            print(f"  Reason: {issue['reason']}")
            
            if not self.auto_recover:
                print("  [AUTO-RECOVER DISABLED] Manual intervention required")
                continue
            
            try:
                print("  Attempting recovery...")
                
                if issue["type"] == "stuck_pending":
                    self._recover_pending(issue["history_id"])
                elif issue["type"] == "stuck_applying":
                    self._recover_applying(issue["history_id"], manager)
                else:
                    raise ValueError(f"Unknown issue type: {issue['type']}")
                
                results["recovered"] += 1
                results["details"].append({
                    "tweak_id": issue["tweak_id"],
                    "status": "recovered"
                })
                print("  Recovered successfully")
                
            except Exception as error:
                results["failed"] += 1
                results["details"].append({
                    "tweak_id": issue["tweak_id"],
                    "status": "failed",
                    "error": str(error)
                })
                print(f"  Recovery failed: {error}")
        
        return results
    
    def _recover_pending(self, history_id: int) -> None:
        self._mark_recovered(
            history_id,
            error_message="Auto-recovered from pending state (no actions executed)"
        )
    
    def _recover_applying(self, history_id: int, manager) -> None:
        manager._rollback(history_id)
        
        self._mark_recovered(
            history_id,
            error_message="Auto-recovered from applying state (changes rolled back)"
        )
    
    def _mark_recovered(self, history_id: int, error_message: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tweak_history
            SET status = 'recovered', 
                error_message = ?
            WHERE id = ?
        """, (error_message, history_id))
        
        conn.commit()
        conn.close()


def mark_applying(history_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tweak_history
        SET status = 'applying'
        WHERE id = ?
    """, (history_id,))
    
    conn.commit()
    conn.close()