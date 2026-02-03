# Luxmed Sniper

**Luxmed Sniper** is an automated tool designed to monitor the Luxmed patient portal for available medical appointments. It addresses the challenge of finding specific or urgent appointments by continuously checking for open slots based on your criteria and sending instant notifications when a match is found.

## How to use LuxmedSniper?

1.  **Install dependencies:**
    Using `uv` (recommended):
    ```bash
    uv sync --extra all
    ```
    Or install specific extras if you don't need all providers:
    ```bash
    uv pip install -e .[telegram,slack]
    ```
2. Create Configuration File
Create a `config.yaml` file (or multiple files). Here is a complete example:

```yaml
luxmed:
  login: "YOUR_LOGIN"   # Your Luxmed Portal login
  password: "PASSWORD"  # Your Luxmed Portal password

luxmedsniper:
  lookup_time_days: 14  # Search window: Look for appointments in the next 14 days
  facilities_ids: []    # Optional: Global list of preferred facility IDs (empty = all)

  # List of notification providers to enable
  notification_provider:
    - pushover
    # - pushover
    # - slack

  doctor_locators:
    - name: "Warsaw - Ophthalmologist"
      # Format: cityId*serviceId*facilitiesIds*doctorsIds
      # Use -1 for "any" in facilities or doctors
      id: "1*7681*-1*-1"
      enabled: true

    - name: "Specific Doctor"
      # Example: City 1, Service 7222, Any Facility, Specific Doctor ID 83332
      id: "1*7222*-1*83332"
      enabled: true

# --- Notification Providers Configuration ---
pushover:
  user_key: # Your pushover.net user key
  api_token:  # pushover.net App API Token
  message_template: "New visit! {AppointmentDate} at {ClinicPublicName} - {DoctorName}"
  title: "New Lux Med visit available!" # Pushover message topic
misc:
  notifydb: "./notifications.db" # State file used to remember which notifications has been sent already
```

### The `id` Format
The `id` field in `doctor_locators` is a string containing four parts separated by asterisks (`*`):
`CityID * ServiceID * FacilityIDs * DoctorIDs`

*   **CityID**: ID of the city (e.g., `1` for Warsaw).
*   **ServiceID**: ID of the specialization/service (e.g., `7409`).
*   **FacilityIDs**: Comma-separated IDs of specific clinics, or `-1` for any.
*   **DoctorIDs**: Comma-separated IDs of specific doctors, or `-1` for any.

## Usage

### Running Locally
Run the script passing your configuration file(s). You can list multiple files to merge them.

```bash
uv run luxmed_sniper.py -c credentials.yaml config.yaml
```
or in case you split the configuration into separate config files
```bash
uv run luxmed_sniper.py -c configs/{antoni,pediatra,providers,blisko_domu}.yaml
```

**Options:**
*   `-c`, `--config`: Path(s) to configuration file(s).
*   `-d`, `--delay`: Time in seconds between checks (default: 1800s / 30m).

### Running with Docker

1.  Set up your `luxmed_sniper.yaml` (or similar).
2.  Use the provided `docker-compose.yml`:
    ```bash
docker-compose up -d
```
*Note: Ensure your `docker-compose.yml` mounts your configuration file correctly.*

## Warning

**Please use this tool responsibly.**
Running queries too frequently (e.g., every few seconds) may trigger Luxmed's security systems.
*   **Temporary Lock:** Breaching the "fair use policy" may lock your account for 24 hours.
*   **Permanent Lock:** Repeated breaches can lead to an indefinite lock requiring manual intervention from Luxmed support.
*   **Recommendation:** Keep the delay reasonable (e.g., default 30 minutes or more).

## Disclaimer
This project is an independent tool and is **not** affiliated with, endorsed by, or connected to LUX MED. Use it at your own risk.
