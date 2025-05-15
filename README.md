# SkyBlock Analytics API
This API provides time-series and summary endpoints for various SkyBlock market data sources: Bazaar, Auction House (BIN and sold), Firesales, ItemSales, and Election results.

---

## Available Endpoints

```
https://https://pulsion-apiv1.up.railway.app
```

| Method | Path                | Description                                                                                  |
| ------ | ------------------- | -------------------------------------------------------------------------------------------- |
| GET    | `/items`            | List all tracked item IDs in Bazaar & AuctionsLB (lowest BIN).                               |
| GET    | `/prices/{item_id}` | Time series of price data (BIN or Bazaar). Add `?range=` to select window (default `1week`). |
| GET    | `/sold/{item_id}`   | Bazaar-only: amount sold derived from `buyMovingWeek` across given range (use `?range=`).    |
| GET    | `/firesales`        | List firesale events (item\_id & timestamp).                                                 |
| GET    | `/item_sales`       | Raw auction sales counts per timestamp (ItemSale table).                                     |
| GET    | `/elections`        | List mayoral elections with year, mayor name, and timestamp.                                 |
| GET    | `/docs`             | Interactive Swagger UI (auto-generated OpenAPI docs).                                        |
| GET    | `/redoc`            | Alternative ReDoc documentation view.                                                        |
| GET    | `/openapi.json`     | OpenAPI schema JSON file.                                                                    |
