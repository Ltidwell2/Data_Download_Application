

from fastapi import FastAPI, HTTPException, BackgroundTasks, background
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
import uvicorn

# File Imports
from receipt_print import receipt_main
from look_download import get_csv_for_look
from connection import generic_sdk



import os

generic_sdk = generic_sdk()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/receipt")
async def receipt_print(background_tasks: BackgroundTasks, invoice_no: str, date: str):
    print(type(invoice_no))
    print(type(date))
    try:
        pdf_path = receipt_main(invoice_no, date)
        response = FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))

        # Add a background task to delete the file after sending the response
        background_tasks.add_task(deleted_file, pdf_path)

        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/look-csv")
async def get_csv(background_tasks: BackgroundTasks,look_id: str): #generic_sdk,
    look = get_csv_for_look(generic_sdk, look_id)
    # convert to csv and return
    csv_file_path = "look.csv"
    with open(csv_file_path, "w") as f:
        f.write(look)
    
    background_tasks.add_task(deleted_file, csv_file_path)
    
    return FileResponse(csv_file_path, media_type='text/csv', filename="look.csv")

def deleted_file(file_path: str):
    try:
        os.remove(file_path)
    except Exception as e:
        # Log the error if needed
        print(f"Error deleting file: {e}")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

