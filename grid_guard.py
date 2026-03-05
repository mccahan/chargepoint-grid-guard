#!/usr/bin/env python3
"""
ChargePoint Grid Guard

Monitors Tesla Powerwall grid status and stops EV charging when the grid goes offline.
This prevents the Powerwall from draining while trying to charge the car during an outage.
"""

import os
import sys
import time
import logging
import requests
from python_chargepoint import ChargePoint

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Configuration from environment
CHARGEPOINT_USERNAME = os.environ.get("CHARGEPOINT_USERNAME")
CHARGEPOINT_PASSWORD = os.environ.get("CHARGEPOINT_PASSWORD")
POWERWALL_URL = os.environ.get("POWERWALL_URL", "http://pypowerwall:8675")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))
RESUME_CHARGING = os.environ.get("RESUME_CHARGING", "false").lower() == "true"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


class GridGuard:
    def __init__(self):
        self.validate_config()
        self.chargepoint = ChargePoint(
            username=CHARGEPOINT_USERNAME,
            password=CHARGEPOINT_PASSWORD
        )
        self.last_grid_status = None
        self.stopped_session_id = None
        logger.info(f"Grid Guard initialized (poll interval: {POLL_INTERVAL}s)")
        logger.info(f"Powerwall URL: {POWERWALL_URL}")
        logger.info(f"Resume charging on grid restore: {RESUME_CHARGING}")
        if DRY_RUN:
            logger.warning("DRY RUN MODE - No charging actions will be taken")

    def validate_config(self):
        if not CHARGEPOINT_USERNAME or not CHARGEPOINT_PASSWORD:
            logger.error("CHARGEPOINT_USERNAME and CHARGEPOINT_PASSWORD are required")
            sys.exit(1)

    def get_grid_status(self) -> bool:
        """Query pypowerwall for grid status. Returns True if grid is online."""
        try:
            response = requests.get(f"{POWERWALL_URL}/csv/v2", timeout=10)
            response.raise_for_status()
            
            # Parse CSV: Grid,Home,Solar,Battery,BatteryLevel,GridStatus,Reserve
            lines = response.text.strip().split("\n")
            if not lines or not lines[0]:
                logger.warning("Empty pypowerwall response")
                return True  # Assume online if we can't parse
            
            # Skip header if present (first line starts with "Grid")
            data_line = lines[1] if len(lines) > 1 and lines[0].startswith("Grid") else lines[0]
            values = data_line.split(",")
            
            if len(values) >= 6:
                grid_status = int(float(values[5]))  # GridStatus: 1=online, 0=offline
                return grid_status == 1
            
            logger.warning("Could not parse grid status from response")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to query Powerwall: {e}")
            return True  # Assume online if we can't reach pypowerwall
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse Powerwall response: {e}")
            return True

    def get_charging_status(self):
        """Get current ChargePoint charging session if any."""
        try:
            return self.chargepoint.get_user_charging_status()
        except Exception as e:
            logger.error(f"Failed to get charging status: {e}")
            return None

    def stop_charging(self, session_id: int) -> bool:
        """Stop an active charging session."""
        if DRY_RUN:
            logger.info(f"[DRY RUN] Would stop charging session {session_id}")
            return True
            
        try:
            session = self.chargepoint.get_charging_session(session_id)
            session.stop()
            logger.info(f"Stopped charging session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop charging session: {e}")
            return False

    def start_charging(self, device_id: int) -> bool:
        """Start a new charging session."""
        if DRY_RUN:
            logger.info(f"[DRY RUN] Would start charging on device {device_id}")
            return True
            
        try:
            self.chargepoint.start_charging_session(device_id)
            logger.info(f"Started charging on device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start charging: {e}")
            return False

    def handle_grid_offline(self):
        """Handle grid going offline - stop any active charging."""
        charging = self.get_charging_status()
        if charging:
            logger.warning(f"Grid offline! Stopping charging session {charging.session_id}")
            if self.stop_charging(charging.session_id):
                self.stopped_session_id = charging.session_id
                # Store device ID for potential resume
                session = self.chargepoint.get_charging_session(charging.session_id)
                self.stopped_device_id = session.device_id
        else:
            logger.info("Grid offline but no active charging session")

    def handle_grid_online(self):
        """Handle grid coming back online - optionally resume charging."""
        if RESUME_CHARGING and hasattr(self, 'stopped_device_id') and self.stopped_device_id:
            logger.info(f"Grid restored! Resuming charging on device {self.stopped_device_id}")
            if self.start_charging(self.stopped_device_id):
                self.stopped_device_id = None
                self.stopped_session_id = None
        else:
            logger.info("Grid restored")

    def run(self):
        """Main monitoring loop."""
        logger.info("Starting Grid Guard monitoring loop")
        
        while True:
            try:
                grid_online = self.get_grid_status()
                
                # Detect state change
                if self.last_grid_status is not None:
                    if self.last_grid_status and not grid_online:
                        # Grid just went offline
                        self.handle_grid_offline()
                    elif not self.last_grid_status and grid_online:
                        # Grid just came back online
                        self.handle_grid_online()
                
                # Log current status periodically
                status = "ONLINE" if grid_online else "OFFLINE"
                if self.last_grid_status != grid_online:
                    logger.info(f"Grid status: {status}")
                
                self.last_grid_status = grid_online
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(POLL_INTERVAL)


def main():
    guard = GridGuard()
    guard.run()


if __name__ == "__main__":
    main()
