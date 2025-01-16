from fastapi import FastAPI
import ntplib
import pendulum
from typing import Optional

app = FastAPI()

def format_gmt_offset(dt: pendulum.DateTime) -> str:
    """
    Format the GMT offset accurately using pendulum's built-in offset handling.
    Returns format like 'GMT +5:30' or 'GMT -4:00'
    """
    # Get total offset in seconds
    offset_seconds = dt.offset
    
    # Convert to hours and minutes
    total_minutes = offset_seconds // 60
    hours = total_minutes // 60
    minutes = abs(total_minutes % 60)
    
    # Determine sign
    sign = '+' if offset_seconds >= 0 else '-'
    
    return f"GMT {sign}{abs(hours):02d}:{minutes:02d}"

@app.get("/time")
async def get_server_time(timezone: str = "America/Argentina/San_Juan"):
    """
    Fetch current time from NIST server and return UTC, GMT, and local timezone times
    with accurate offset calculations.
    
    Args:
        timezone (str): Target timezone (default: "Asia/Kolkata")
    
    Returns:
        dict: Contains UTC, GMT, and local timezone times with precise offsets
    """
    try:
        # Get NTP time
        client = ntplib.NTPClient()
        response = client.request("time.nist.gov", version=3)
        
        # Get UTC time
        utc_dt = pendulum.from_timestamp(response.tx_time)
        
        # Convert to requested timezone
        local_dt = utc_dt.in_timezone(timezone)
        
        # Calculate precise offset
        offset_seconds = local_dt.offset
        offset_hours = offset_seconds / 3600  
        
        # Get GMT format with offset
        gmt_format = format_gmt_offset(local_dt)
        
        return {
            "timestamp": int(response.tx_time),
            "times": {
                "utc": {
                    "date": utc_dt.format('YYYY-MM-DD'),
                    "time": utc_dt.format('HH:mm:ss'),
                    "timezone": "UTC",
                    "offset_seconds": 0,
                    "offset_hours": 0
                },
                "gmt": {
                    "date": local_dt.format('YYYY-MM-DD'),
                    "time": local_dt.format('HH:mm:ss'),
                    "timezone": gmt_format,
                    "offset_seconds": offset_seconds,
                    "offset_hours": offset_hours
                },
                "local": {
                    "date": local_dt.format('YYYY-MM-DD'),
                    "time": local_dt.format('HH:mm:ss'),
                    "timezone": timezone,
                    "offset_seconds": offset_seconds,
                    "offset_hours": offset_hours,
                    "is_dst": local_dt.is_dst()  
                }
            },
            "status": "success"
        }
        
    except ntplib.NTPException as e:
        return {
            "status": "error",
            "message": f"NTP server error: {str(e)}"
        }
    except pendulum.exceptions.ParserError as e:
        return {
            "status": "error",
            "message": f"Invalid timezone: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)