from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ntplib import NTPClient, NTPStats
import pytz
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NTPResponse(BaseModel):
    time_server: str
    received_ntp_time: str
    offset_ms: int
    round_trip_time_ms: int
    stratum: int
    system_time: str
    last_sync: str
    timezone_offset: str

class DetailedNTPSync:
    def __init__(self):
        self.ntp_client = NTPClient()
        self.primary_server = "time.nist.gov"
        self.backup_servers = [
            "pool.ntp.org",
            "time.google.com",
            "time.windows.com"
        ]
        self.last_successful_sync = None
        self.last_response = None

    async def get_detailed_time(self) -> NTPResponse:
        try:
            # Get NTP response
            response = await asyncio.to_thread(
                self.ntp_client.request,
                self.primary_server,
                version=3,
                timeout=5
            )
            
            # Store last successful response
            self.last_response = response
            self.last_successful_sync = datetime.now()

            # Calculate precise times
            ntp_time = datetime.fromtimestamp(response.tx_time, pytz.UTC)
            system_time = datetime.now(pytz.UTC)
            
            # Get local timezone offset
            local_tz = datetime.now().astimezone().tzinfo
            tz_offset = datetime.now(local_tz).strftime('%z')

            return NTPResponse(
                time_server=self.primary_server,
                received_ntp_time=ntp_time.strftime("%H:%M:%S"),
                offset_ms=int(response.offset * 1000),  # Convert to milliseconds
                round_trip_time_ms=int(response.delay * 1000),  # Convert to milliseconds
                stratum=response.stratum,
                system_time=system_time.strftime("%H:%M:%S.%f")[:-4],
                last_sync=self.last_successful_sync.strftime("%H:%M:%S"),
                timezone_offset=tz_offset
            )

        except Exception as e:
            logger.error(f"Primary server failed: {str(e)}")
            # Try backup servers
            for server in self.backup_servers:
                try:
                    response = await asyncio.to_thread(
                        self.ntp_client.request,
                        server,
                        version=3,
                        timeout=5
                    )
                    logger.info(f"Successfully failed over to {server}")
                    return NTPResponse(
                        time_server=server,
                        received_ntp_time=datetime.fromtimestamp(response.tx_time).strftime("%H:%M:%S"),
                        offset_ms=int(response.offset * 1000),
                        round_trip_time_ms=int(response.delay * 1000),
                        stratum=response.stratum,
                        system_time=datetime.now().strftime("%H:%M:%S.%f")[:-4],
                        last_sync=datetime.now().strftime("%H:%M:%S"),
                        timezone_offset=datetime.now().astimezone().strftime('%z')
                    )
                except:
                    continue
            
            raise HTTPException(
                status_code=503,
                detail="Failed to reach any NTP servers"
            )

    def get_sync_status(self) -> str:
        if not self.last_successful_sync:
            return "No sync yet"
        
        time_diff = (datetime.now() - self.last_successful_sync).total_seconds()
        if time_diff < 120:  # 2 minutes
            return "Last timestamp received less than 2 minutes ago"
        else:
            return f"Last sync was {int(time_diff)} seconds ago"

app = FastAPI(title="Detailed NTP Time Service")
ntp_sync = DetailedNTPSync()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/time", response_model=NTPResponse)
async def get_ntp_time():
    """Get detailed NTP time synchronization information"""
    return await ntp_sync.get_detailed_time()

@app.get("/status")
async def get_status():
    """Get sync status information"""
    return {
        "status": ntp_sync.get_sync_status(),
        "server": ntp_sync.primary_server,
        "last_sync": ntp_sync.last_successful_sync.isoformat() if ntp_sync.last_successful_sync else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)