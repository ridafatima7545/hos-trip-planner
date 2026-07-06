NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
USER_AGENT = "spotter-ai-hos-assessment/1.0"
REQUEST_TIMEOUT_SECONDS = 20

EARTH_RADIUS_MILES = 3958.7613
METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600
ROAD_DISTANCE_FALLBACK_MULTIPLIER = 1.18
FALLBACK_SPEED_MPH = 55.0

MAX_DRIVE_SHIFT_HOURS = 11.0
MAX_DUTY_WINDOW_HOURS = 14.0
MAX_DRIVE_BEFORE_BREAK_HOURS = 8.0
BREAK_HOURS = 0.5
REST_HOURS = 10.0
RESTART_HOURS = 34.0
CYCLE_LIMIT_HOURS = 70.0
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
FUEL_INTERVAL_MILES = 1000.0
FUEL_HOURS = 0.5

MIN_PROGRESS_HOURS = 0.01
MIN_REQUIRED_CYCLE_HOURS = 0.25
DEFAULT_START_HOUR = 8

STATUS_OFF = "OFF"
STATUS_SLEEPER = "SB"
STATUS_DRIVING = "DRIVING"
STATUS_ON_DUTY = "ON"

REMARK_FUEL = "Fuel stop"
REMARK_PICKUP = "Pickup loading and paperwork"
REMARK_DROPOFF = "Dropoff unloading and paperwork"
REMARK_BREAK = "30-minute rest break after 8 hours of driving"
REMARK_RESTART = "34-hour restart to restore 70-hour/8-day cycle"
REMARK_REST_MORE_DUTY = "10-hour off-duty reset before more on-duty time"
REMARK_REST_BEFORE_BREAK = "10-hour off-duty reset before required 30-minute break"
REMARK_REST_DRIVE_LIMIT = "10-hour off-duty reset after reaching 11-hour driving limit"
REMARK_REST_DUTY_WINDOW = "10-hour off-duty reset after reaching 14-hour duty window"

DAILY_TOTAL_STATUSES = {
    STATUS_OFF: 0.0,
    STATUS_SLEEPER: 0.0,
    STATUS_DRIVING: 0.0,
    STATUS_ON_DUTY: 0.0,
}

ASSUMPTIONS = [
    "Property-carrying driver under the 70-hour/8-day cycle.",
    "No adverse driving conditions or short-haul exceptions.",
    "Pickup and dropoff each take 1 on-duty hour.",
    "Fueling is planned at least once every 1,000 miles and takes 30 minutes.",
    "A 34-hour restart is inserted when the supplied cycle hours leave no legal on-duty time.",
]
