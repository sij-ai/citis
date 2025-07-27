# **Complete ChangeDetection.io API Integration Guide for Citis Content Integrity Monitoring**

## **Authentication**
All API requests require an API key header:
```
x-api-key: YOUR_API_KEY_HERE
```

---

## **Part 1: One-Time ChangeDetection.io Configuration**

**Goal:** Configure changedetection.io to send all change notifications to a dedicated citis webhook endpoint.

**Endpoint:** `POST /api/v1/notifications`

**Important:** The notification URL must use the `json://` prefix to ensure POST requests with JSON payloads.

**Example Request:**
```bash
curl http://<your-changedetection-host>:5000/api/v1/notifications \
-H"x-api-key:<your-api-key>" \
-H "Content-Type: application/json" \
-d '{"notification_urls": ["json://citis.app/api/internal/webhook/changedetection"]}'
```

---

## **Part 2: Core Workflow for Citable Archive Creation**

Execute this workflow every time a premium user creates a citable archive.

### **Prerequisites:**
1. Store changedetection.io base URL and API key as environment variables
2. Define premium tier to frequency mapping:
```javascript
const PLAN_FREQUENCIES = {
  'bronze_tier': { days: 1 },          // Daily checks
  'silver_tier': { hours: 6 },         // Every 6 hours  
  'gold_tier': { minutes: 30 }         // Every 30 minutes
};
```

### **Step 1: Check if URL is Already Monitored**

**Endpoint:** `GET /api/v1/watch`

**Logic:**
1. Fetch all existing watches
2. Iterate through the response object (keys are UUIDs, values are watch objects)
3. Check if any watch has a `url` property matching the target URL exactly
4. If match found: store the `uuid` and proceed to **Step 2**
5. If no match found: proceed to **Step 3**

**Example Request:**
```bash
curl http://<your-changedetection-host>:5000/api/v1/watch \
-H"x-api-key:<your-api-key>"
```

**Response Format:**
```json
{
    "watch-uuid-1": {
        "url": "https://example.com/page",
        "title": "Page Title",
        "last_changed": 1677103794,
        "last_checked": 1677103794
    }
}
```

### **Step 2: URL Exists - Evaluate and Update Frequency**

**Endpoint:** `GET /api/v1/watch/:uuid` (to get full details including frequency)

**Logic:**
1. Get the complete watch details to access `time_between_check`
2. Convert both existing and required frequencies to total seconds for comparison
3. **Lower seconds = more frequent checks**
4. Update if `current_interval_seconds > required_interval_seconds`

**Frequency Conversion Helper:**
```javascript
function convertToSeconds(timeObj) {
    return (timeObj.weeks || 0) * 604800 + 
           (timeObj.days || 0) * 86400 + 
           (timeObj.hours || 0) * 3600 + 
           (timeObj.minutes || 0) * 60 + 
           (timeObj.seconds || 0);
}
```

**Update Request (if needed):**
```bash
curl http://<your-changedetection-host>:5000/api/v1/watch/<existing-uuid> -X PUT \
-H"x-api-key:<your-api-key>" \
-H "Content-Type: application/json" \
-d '{
    "time_between_check": {
        "minutes": 30
    }
}'
```

### **Step 3: URL Doesn't Exist - Create New Watch**

**Endpoint:** `POST /api/v1/watch`

**Required Fields:**
- `url`: The URL to monitor
- `time_between_check`: Frequency object based on user's plan
- `notification_format`: Set to `"json"`
- `notification_body`: Stringified JSON with Jinja2 templates

**Example Request:**
```bash
curl http://<your-changedetection-host>:5000/api/v1/watch -X POST \
-H"x-api-key:<your-api-key>" \
-H "Content-Type: application/json" \
-d '{
    "url": "https://example.com/article",
    "title": "Citis Archive Monitor: example.com/article",
    "time_between_check": {
        "hours": 6
    },
    "notification_format": "json",
    "notification_body": "{ \\"watch_uuid\\": \\"{{watch_uuid}}\\", \\"source_url\\": \\"{{watch_url}}\\", \\"change_detected_at\\": \\"{{last_changed}}\\", \\"diff_plaintext\\": \\"{{diff_plaintext}}\\", \\"diff_html\\": \\"{{diff}}\\", \\"title\\": \\"{{title}}\\" }"
}'
```

**Critical Note on JSON Escaping:** The double backslashes `\\"` in `notification_body` are required to properly escape quotes within the JSON string.

---

## **Complete API Endpoint Reference**

| Endpoint | Method | Purpose | Key Fields |
|----------|---------|---------|------------|
| `/api/v1/notifications` | `POST` | **One-time:** Register webhook URL | `notification_urls` array |
| `/api/v1/watch` | `GET` | **Step 1:** List all watches to find URL matches | Response: `{uuid: {url, title, ...}}` |
| `/api/v1/watch/:uuid` | `GET` | **Step 2:** Get full watch details including frequency | Response includes `time_between_check` |
| `/api/v1/watch` | `POST` | **Step 3:** Create new watch | `url`, `time_between_check`, `notification_format`, `notification_body` |
| `/api/v1/watch/:uuid` | `PUT` | **Step 2:** Update existing watch frequency | `time_between_check` |

---

## **Data Structure Reference**

### **`time_between_check` Object:**
```json
{
    "weeks": 0,
    "days": 0, 
    "hours": 6,
    "minutes": 0,
    "seconds": 0
}
```
*All fields are optional integers. Combine as needed (e.g., `{"days": 1, "hours": 12}`).*

### **Notification Payload Template:**
**In API request (escaped):**
```json
"{ \\"watch_uuid\\": \\"{{watch_uuid}}\\", \\"source_url\\": \\"{{watch_url}}\\", \\"diff_plaintext\\": \\"{{diff_plaintext}}\\", \\"diff_html\\": \\"{{diff}}\\", \\"change_detected_at\\": \\"{{last_changed}}\\", \\"title\\": \\"{{title}}\\" }"
```

**Received by webhook (clean JSON):**
```json
{
  "watch_uuid": "cc0cfffa-f449-477b-83ea-0caafd1dc091",
  "source_url": "https://example.com/article",
  "diff_plaintext": "Text showing changes...",
  "diff_html": "<span>HTML diff markup...</span>",
  "change_detected_at": "1677103794",
  "title": "Watch Title"
}
```

### **Available Jinja2 Template Variables:**
- `{{watch_uuid}}`: Unique identifier for the watch
- `{{watch_url}}`: The monitored URL
- `{{diff_plaintext}}`: Plain text diff of changes
- `{{diff}}`: HTML formatted diff
- `{{last_changed}}`: Timestamp of last change
- `{{title}}`: Watch title
- `{{diff_full}}`: Complete diff information

---

## **Error Handling**
- **200**: Success
- **201**: Created (for POST operations)
- **400**: Invalid input (check JSON structure)
- **404**: Watch UUID not found
- **500**: Server error

---

## **Citis Webhook Endpoint Requirements**

Your `/api/internal/webhook/changedetection` endpoint must:

1. **Accept POST requests** with JSON content-type
2. **Parse the JSON payload** to extract:
   - `source_url`: Identify affected citable archives
   - `diff_plaintext`/`diff_html`: Analyze content changes
   - `watch_uuid`: For potential API calls back to changedetection.io
3. **Query your database** to find all citable archives for the `source_url`
4. **Process content integrity alerts** based on the diff information
5. **Handle errors gracefully** and log for debugging
