from langchain_core.tools import tool
from typing import Dict
import requests
from datetime import datetime, timezone
from schema_agent import CreateServiceRequestInput, GetSR

API_URL = "http://103.86.135.88:7003/ords/ws_apparel/erp_it_service_request/apparel"


# ================================
# CREATE SERVICE REQUEST TOOL
# ================================
@tool("create_service_request", args_schema=CreateServiceRequestInput, return_direct=True)
def create_service_request(**kwargs) -> Dict:
    """
    Creates a new Service Request (SR) in the ERP/IT system.
    Uses POST API to submit an SR with all required fields.
    """
    try:
        input_data = CreateServiceRequestInput(**kwargs)  # Validate and create model from kwargs
        payload = input_data.model_dump()  # ✅ field names match schema
        headers = {"Content-Type": "application/json"}

        response = requests.post(API_URL, json=payload, headers=headers, timeout=25)

        if response.status_code in [200, 201]:
            return {
                "status": "success",
                "message": "✅ Service Request created successfully",
                "response": response.json(),
            }
        else:
            return {
                "status": "failed",
                "code": response.status_code,
                "message": response.text,
            }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ================================
# GET SERVICE REQUEST TOOL
# ================================
@tool("get_sr", args_schema=GetSR, return_direct=True)
def get_sr(**kwargs) -> Dict:
    """
    🔍 Fetch or analyze Service Requests (SRs) via GET API.
    Supports filters like: all, by_ticket, by_creator, by_status, etc.
    """
    try:
        input_data = GetSR(**kwargs)  # Validate and create model from kwargs
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        sr_list = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(sr_list, list):
            return {"status": "error", "message": "Unexpected API response format"}

        query = (input_data.query_type or "").lower().strip()
        now = datetime.now(timezone.utc)

        # === all ===
        if query == "all":
            return {"total_records": len(sr_list), "sample": sr_list[:5]}

        # === by_ticket ===
        if query == "by_ticket" and input_data.ticket_no:
            for sr in sr_list:
                if sr.get("ticket_no") == input_data.ticket_no:
                    return {
                        "ticket_no": sr.get("ticket_no"),
                        "status": sr.get("task_status"),
                        "application_name": sr.get("application_name"),
                        "description": sr.get("description"),
                        "created_by": sr.get("created_by"),
                        "created_on": sr.get("created_on"),
                        "developer_remarks": sr.get("developer_remarks"),
                        "completion_date": sr.get("completion_date"),
                    }
            return {"message": f"No record found for ticket_no {input_data.ticket_no}"}

        # === by_creator ===
        if query == "by_creator" and input_data.created_by:
            results = [
                sr for sr in sr_list
                if (sr.get("created_by") or "").lower() == input_data.created_by.lower()
            ]
            return {"created_by": input_data.created_by, "total": len(results), "records": results[:5]}

        # === by_status ===
        if query == "by_status" and input_data.task_status:
            results = [
                sr for sr in sr_list
                if (sr.get("task_status") or "").lower() == input_data.task_status.lower()
            ]
            return {"status": input_data.task_status, "count": len(results), "sample": results[:5]}

        # === by_department ===
        if query == "by_department" and input_data.department:
            results = [
                sr for sr in sr_list
                if (sr.get("department") or "").lower() == input_data.department.lower()
            ]
            return {"department": input_data.department, "count": len(results), "sample": results[:5]}

        # === summary ===
        if query == "summary":
            total = len(sr_list)
            completed = sum(1 for sr in sr_list if (sr.get("task_status") or "").lower() == "completed")
            pending = total - completed
            high_priority = sum(1 for sr in sr_list if (sr.get("pariority_level") or "").lower() == "high")
            return {
                "summary": {
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                    "high_priority": high_priority,
                }
            }

        # === overdue ===
        if query == "overdue":
            overdue_srs = []
            for sr in sr_list:
                status = (sr.get("task_status") or "").lower()
                created_on = sr.get("created_on")
                if status != "completed" and created_on:
                    try:
                        created_dt = datetime.fromisoformat(created_on.replace("Z", "+00:00"))
                        days_pending = (now - created_dt).days
                        if days_pending > 2:
                            overdue_srs.append({
                                "ticket_no": sr.get("ticket_no"),
                                "days_pending": days_pending,
                                "status": sr.get("task_status"),
                                "application": sr.get("application_name"),
                                "created_on": created_on,
                            })
                    except Exception:
                        continue
            return {"overdue_count": len(overdue_srs), "records": overdue_srs[:10]}

        return {"message": "Invalid query type or missing required parameters."}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ================================
# EXPORT TOOLS LIST
# ================================
tools = [create_service_request, get_sr]