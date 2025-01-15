from fastapi import FastAPI
import ntplib
from datetime import timezone, datetime
import pytz

app = FastAPI()

@app.get("/")
async def get_server_time():
    """
    Fetch and return the current time from the NIST time server, including conversions to Asia/Kolkata and UTC.

    Returns:
        dict: A dictionary containing:
            - 'utc_time': UTC time in ISO format.
            - 'kolkata_time': Time in Asia/Kolkata timezone in ISO format.
            - 'server_time': Original server time in UTC as previously provided.
    """
    try:
        # Create an instance of the NTPClient
        c = ntplib.NTPClient()
        
        # Query the time server
        response = c.request('time.nist.gov', version=3)
        
        # Convert the timestamp to a datetime object with UTC timezone
        server_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
        
        # Calculate Asia/Kolkata time using pytz
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        kolkata_time = server_time.astimezone(kolkata_tz)
        
        # UTC time is already in UTC, but we'll format it for consistency
        utc_time = server_time

        return {
            "server_time": server_time.isoformat(),
            "kolkata_time": kolkata_time.isoformat(),
            "utc_time": utc_time.isoformat()
        }
    
    except ntplib.NTPException as e:
        return {"error": f"Could not fetch time from server: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)