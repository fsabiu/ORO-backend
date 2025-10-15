#### **API Endpoint: Trigger Detection and Analysis**

**Endpoint:** `POST /detect`
**Purpose:** To initiate a new, asynchronous detection and analysis job. This endpoint **does not** wait for the processing to complete. It validates the request, creates the initial report record, and triggers a background task.

**Request Body (JSON):**
```json
{
  "image_name": "port_of_la_oct16.tif",
  "report_name": "Port Activity Monitoring - Oct 16",
  "model_id": "vehicle-detector-v1.2",
  "confidence_threshold": 0.85,
  "author_id": 12345,
  "ruleset_ids": [1, 5, 12]
}
```
*   `image_name`: The filename of the GeoTIFF that **must already exist** in the object storage bucket.
*   `report_name`: The user-friendly name for this analysis report.
*   `model_id`: Identifier for the ML model to be used by the worker.
*   `confidence_threshold`: The minimum confidence score (0.0 to 1.0) for a detection to be saved.
*   `author_id`: The ID of the user initiating the request.
*   `ruleset_ids`: An array of `id`s from the `RULESETS` table to check against.

**Synchronous Actions (Immediate Response):**
1.  **Validation:**
    *   Check that all required fields in the request body are present.
    *   Verify that `image_name` exists in the object storage bucket.
    *   Verify that all `ruleset_ids` exist in the `RULESETS` table.
    *   If any validation fails, return `400 Bad Request` or `404 Not Found` with a clear error message.
2.  **Report Creation:**
    *   `INSERT` a new record into the `REPORTS` table with the provided `name` and `bucket_img_path` (`image_name`). The `image_footprint` column will be `NULL` at this stage.
3.  **Task Delegation:**
    *   Launch an asynchronous background job (e.g., using Celery).
    *   Pass all necessary information to the job: the newly created `report_id`, `model_id`, `confidence_threshold`, and the `ruleset_ids` array.
4.  **Response:**
    *   Return `202 Accepted` to the client. The response body should include the `report_id` so the frontend can track its progress.
    ```json
    {
      "message": "Detection job accepted for processing.",
      "report_id": 102
    }
    ```

**Asynchronous Actions (Background Worker Logic):**
This is the step-by-step process executed by the background worker.

1.  **Initialization:** The worker starts with the `report_id` and other job parameters.
2.  **Metadata Extraction:**
    *   Fetch the `bucket_img_path` from the `REPORTS` table using the `report_id`.
    *   Open the GeoTIFF from object storage using `rasterio`.
    *   Extract the full geographic boundary (`image_footprint`) and the image's CRS.
    *   Convert the `image_footprint` into an Oracle `SDO_GEOMETRY` object.
    *   `UPDATE` the `REPORTS` record to set its `image_footprint`.
3.  **Tiling and Detection:**
    *   Define a tile size (e.g., 512x512) appropriate for the ML model.
    *   Iterate through the entire image using a windowed/tiled reading approach.
    *   **For each tile:**
        a.  Read the tile's pixel data.
        b.  Get the tile's affine `transform` (the key to converting local pixel coordinates to global geographic coordinates).
        c.  Load the ML model specified by `model_id`.
        d.  Run inference on the tile's pixel data.
        e.  The model returns a list of detections. Filter out any detections below the `confidence_threshold`.
4.  **Coordinate Reconstruction and Storage:**
    *   **For each valid detection from the tile:**
        a.  **Absolute Pixel Coords:** Convert the tile-local bounding box to full-image pixel coordinates by adding the tile's column/row offset.
        b.  **Geographic Footprint:** Use the tile's `transform` to convert the four corners of the detection's bounding box into geographic (lat/lon) points.
        c.  **Create Geometry Object:** Construct an `SDO_GEOMETRY` polygon from these geographic points.
        d.  **Database Insert:** `INSERT` a new record into the `DETECTIONS` table, populating `report_id`, `class_name`, `confidence`, the absolute pixel coordinates, and the geographic `footprint` polygon.
5.  **Rule Matching and Notification:**
    *   **Immediately after each detection is inserted:**
        a.  Get the `id` and `footprint` of the newly created detection.
        b.  Execute a single, highly efficient spatial query to see if this detection intersects with any of the rules specified in the job's `ruleset_ids` array.
        ```sql
        SELECT r.id
        FROM RULESETS r
        WHERE r.id IN (:list_of_ruleset_ids) -- Filter by the rules for this job
        AND SDO_ANYINTERACT(r.area_of_interest, :new_detection_footprint) = 'TRUE'
        ```
        c.  **If the query returns any matches:**
            i.  For each matching `ruleset_id`, `INSERT` a new record into the `NOTIFICATIONS` table.
            ii. Push a real-time notification to the frontend via the **Server-Sent Events (SSE)** endpoint. The payload should be rich enough for the UI to display an alert (e.g., `{ "notification_id": 55, "report_name": "...", "ruleset_name": "...", "class_detected": "Vehicle" }`).