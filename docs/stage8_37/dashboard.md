# Web Dashboard User Guide: DS08 GIS Interface

The operational web dashboard is accessible at `http://localhost:8000/` or `http://localhost:8000/dashboard`.

---

## 1. Interface Layout

```
-------------------------------------------------------------------------
| DS08 OPERATIONAL | NASA FIRMS Attribution Dashboard | Model: StaticMLP|
-------------------------------------------------------------------------
| Filters        |                      Interactive Map                 |
|                |                                                      |
| Class Selector |          (•) Red: Industrial Fire                    |
| Min Confidence |          (•) Green: Forest Fire                      |
| CSV Uploader   |          (•) Orange: Agricultural Fire               |
| Statistics     |          (•) Blue: Persistent / Other                |
| Legend         |                                                      |
-------------------------------------------------------------------------
```

---

## 2. Key Features
1. **Interactive Leaflet Map:** Displays thermal event markers across India over CartoDB Dark Matter tiles.
2. **Color-Coded Attribution:**
   - **Red:** Industrial Fire
   - **Green:** Forest Fire
   - **Orange:** Agricultural Fire
   - **Blue:** Persistent / Other Thermal Source
   *(A legend explicitly indicates that marker colors reflect model attribution predictions rather than confirmed ground truth.)*
3. **Filtering Controls:** Filter by predicted target class and set a minimum confidence threshold.
4. **Batch CSV Ingestion:** Upload any NASA FIRMS CSV to automatically parse detections, cluster events, run causal inference, and display new events on the map in real time.
5. **Event Details Drawer:** Clicking any marker reveals:
   - Full 4-class probability distribution bars.
   - Current alert thermal measurements (FRP, brightness temperature).
   - Recurrence evidence level (LOW, MODERATE, STRONG).
   - Nearest registered industrial facility distance.
   - Ecoregion context scores (forest biome vs agricultural heartland).
   - Feature-grounded attribution explanation.
   - Chronological list of satellite passes.
