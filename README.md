# SkyBlock Analytics API
This API provides time-series and summary endpoints for various SkyBlock market data sources: Bazaar, Auction House (BIN and sold), Firesales, ItemSales, and Election results.

---

## Available Endpoints

```
https://https://pulsion-apiv1.up.railway.app
```

| Method | Path                | Description                                                                                  |
| ------ | ------------------- | -------------------------------------------------------------------------------------------- |
| GET    | `/items`            | List all tracked item IDs.                               |
| GET    | `/prices/{item_id}` | Time series of price data. Add `?range=` to select window (default `1week`). |
| GET    | `/sold/{item_id}`   | Amount sold derived from `buyMovingWeek` across given range (use `?range=`).    |
| GET    | `/elections`        | List mayoral elections with year, mayor name, and timestamp.                                 |
| GET    | `/docs`             | Interactive Swagger UI (auto-generated OpenAPI docs).                                        |
| GET    | `/redoc`            | Alternative ReDoc documentation view.                                                        |
| GET    | `/openapi.json`     | OpenAPI schema JSON file.                                                                    |
