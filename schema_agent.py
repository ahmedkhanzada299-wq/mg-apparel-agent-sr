from pydantic import BaseModel, Field
from typing import Literal, Optional


class CreateServiceRequestInput(BaseModel):
    """
    Input schema for creating a new Service Request (SR)
    """

    ORGANIZATION: int = Field(
        300000005178046,
        description="Always use this same ID (300000005178046) as the organization input."
    )
    DEPARTMENT: str = Field(
        "ERP IT",
        description="Default department (ERP IT)."
    )
    TYPE: Literal[
        "Application Setup",
        "Connectivity Issue",
        "Form Error",
        "General Inquiry",
        "Inventory Management",
        "Maintaince Request",
        "New Developement",
        "Order Management",
        "User Creation",
        "Website/Networking/Internet"
    ] = Field(
        ...,
        description="Type of service request. Must be one of the listed options."
    )
    APPLICATION_NAME: Literal[
        "Apparel Apex Application",
        "Gate Paas Application",
        "HRMS Application",
        "IT Support & Network",
        "Oracle Fusion"
    ] = Field(
        ...,
        description="Application involved in the request."
    )
    PARIORITY_LEVEL: Literal["Low", "Moderate", "High"] = Field(
        ...,
        description="Priority level for the SR."
    )
    REQUESTED_COMPLETION_DATE: str = Field(
        ...,
        example="12-11-2025",
        description="Requested completion date in MM-DD-YYYY format (ask user for date every time)."
    )
    DESCRIPTION: str = Field(
        ...,
        description="Brief description of the issue or request."
    )
    CREATED_BY: str = Field(
        ...,
        example="Ahmed Khan",
        description="Username of the person creating the SR (ask user for this every time)."
    )


class GetSR(BaseModel):
    """
    Input schema for fetching Service Requests (GET)
    """

    query_type: Literal[
        "all",
        "by_ticket",
        "by_creator",
        "by_status",
        "by_department",
        "summary",
        "overdue"
    ] = Field(
        ...,
        description="Type of query to run."
    )

    ticket_no: Optional[str] = Field(None, example="SR-0000011", description="Ticket number (e.g., SR-0000011)")
    created_by: Optional[str] = Field(None, description="Filter by creator name")
    task_status: Optional[Literal["New", "In Progress", "Completed"]] = Field(None, description="Filter by SR status")
    department: Optional[Literal["ERP IT", "IT", "HR", "Accounts"]] = Field(None, description="Department filter")
