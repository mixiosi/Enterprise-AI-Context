import sqlite3
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("CapEx_Reconciliation_Engine")

DB_PATH = os.path.join(os.path.dirname(__file__), "capex_erp.db")

@mcp.tool()
def get_master_budget(phase: str) -> str:
    """Retrieve the Master Budget remaining for a specific construction phase."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT RemainingBudget FROM MasterBudget WHERE Phase LIKE ?", (f"%{phase}%",))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return f"Remaining Budget for '{phase}' is ${result[0]:,.2f}."
        return f"Phase '{phase}' not found in Master Budget."
    except Exception as e:
        return f"Database error: {e}"

@mcp.tool()
def reconcile_invoice(invoice_amount: float, phase: str) -> str:
    """Cross-reference an incoming invoice amount against the Master Budget to prevent revenue leakage."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT RemainingBudget FROM MasterBudget WHERE Phase LIKE ?", (f"%{phase}%",))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return "ERROR: Phase not found. Cannot reconcile."
            
        remaining = result[0]
        if invoice_amount > remaining:
            overage = invoice_amount - remaining
            return f"🚨 ALERT: Invoice amount (${invoice_amount:,.2f}) EXCEEDS remaining budget (${remaining:,.2f}) by ${overage:,.2f}. Do not approve!"
        else:
            return f"✅ APPROVED: Invoice amount (${invoice_amount:,.2f}) is within the remaining budget (${remaining:,.2f})."
    except Exception as e:
        return f"Database error: {e}"

if __name__ == "__main__":
    print("Starting CapEx Reconciliation MCP Server...")
    mcp.run(transport='stdio')
