from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routers import contract, event
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(title="eo_tech_challenge", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors on the /event endpoint.
    Returns consistent error format: {"status": "rejected", "message": "..."}
    """
    # Only apply custom format to /event endpoint
    if request.url.path == "/event":
        # Extract the first validation error
        errors = exc.errors()
        if errors:
            error = errors[0]
            field = error.get("loc", [])[-1] if error.get("loc") else "unknown"
            error_type = error.get("type", "")
            raw_msg = error.get("msg", "Validation error")

            # Create user-friendly messages based on field and error type
            if field == "date":
                if "required" in error_type or "missing" in error_type:
                    message = "Date field is required."
                elif "too short" in raw_msg.lower():
                    message = "Invalid date format. Expected format: YYYY-MM-DD"
                elif "separator" in raw_msg.lower():
                    message = "Invalid date format. Expected format: YYYY-MM-DD (use dashes, not slashes)"
                elif "outside expected range" in raw_msg.lower():
                    message = "Invalid date. Day value is outside expected range."
                else:
                    message = f"Invalid date format. {raw_msg}"
            elif field == "type":
                if "required" in error_type or "missing" in error_type:
                    message = "Event type is required."
                else:
                    message = f"Invalid event type format."
            elif field == "contract_number":
                if "required" in error_type or "missing" in error_type:
                    message = "Contract number is required."
                else:
                    message = f"Invalid contract number format."
            elif field == "created_at":
                if "required" in error_type or "missing" in error_type:
                    message = "Created at timestamp is required."
                else:
                    message = f"Invalid created_at format. Expected ISO datetime format."
            else:
                message = f"Invalid {field}: {raw_msg}"

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "rejected",
                    "message": message
                }
            )

    # For other endpoints, return default validation error format
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


# All api routers
app.include_router(contract.router)
app.include_router(event.router)

@app.get("/")
async def root():
    return {"message": "Welcome to EO Tech Challenge API"}
