# FundGenesis API Reference

## Base URL

```
http://localhost:8765
```

## Authentication

Currently, the API does not require authentication. For production deployments, implement API key or OAuth2 authentication.

---

## Endpoints

### Health Check

#### `GET /health`

Returns the service health status.

**Response:**
```json
{
  "status": "ok",
  "service": "FundGenesis API",
  "version": "1.0.0"
}
```

---

### Service Info

#### `GET /`

Returns service information and available endpoints.

**Response:**
```json
{
  "service": "FundGenesis API",
  "version": "1.0.0",
  "description": "Financial Reflexivity Multi-Agent Simulation Platform",
  "endpoints": {
    "simulation": "/api/v1/simulation/run",
    "narrative": "/api/v1/narrative/inject",
    "market": "/api/v1/market/state",
    "agents": "/api/v1/agents/summary",
    "websocket": "/ws"
  }
}
```

---

### Simulation

#### `POST /api/v1/simulation/run`

Run a new simulation with specified parameters.

**Request Body:**
```json
{
  "n_steps": 200,
  "n_retail": 50,
  "n_trend": 20,
  "n_value": 10,
  "initial_price": 100.0,
  "fundamental_value": 100.0,
  "seed": 42,
  "narrative_events": [
    {
      "name": "Tech Boom",
      "category": "fintech",
      "polarity": "positive",
      "intensity": 0.7,
      "timing": 20,
      "duration": 30
    }
  ],
  "shocks": [],
  "enable_reflexivity_game": true,
  "enable_risk_propagation": true,
  "enable_regulator": true
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_steps` | int | 200 | Number of simulation steps (10-5000) |
| `n_retail` | int | 50 | Number of retail agents (1-500) |
| `n_trend` | int | 20 | Number of trend follower agents (0-200) |
| `n_value` | int | 10 | Number of value investor agents (0-100) |
| `initial_price` | float | 100.0 | Initial asset price |
| `fundamental_value` | float | 100.0 | Fundamental value of the asset |
| `seed` | int | null | Random seed for reproducibility |
| `narrative_events` | array | [] | List of narrative events to inject |
| `shocks` | array | [] | List of external shocks |
| `enable_reflexivity_game` | bool | true | Enable game theory analysis |
| `enable_risk_propagation` | bool | true | Enable risk propagation engine |
| `enable_regulator` | bool | true | Enable regulatory agent |

**Response:**
```json
{
  "simulation_id": "uuid-string",
  "status": "completed",
  "summary": {
    "final_price": 125.34,
    "max_bubble_risk": 0.65,
    "max_panic_risk": 0.23,
    "peak_price": 130.50,
    "trough_price": 95.20,
    "total_steps": 200,
    "duration_seconds": 2.45
  }
}
```

---

#### `GET /api/v1/simulation/{simulation_id}`

Get results of a completed simulation.

**Path Parameters:**
- `simulation_id` (string): The simulation ID returned by the run endpoint.

**Response:**
```json
{
  "id": "uuid-string",
  "status": "completed",
  "config": {...},
  "summary": {...},
  "steps": [...]
}
```

---

#### `GET /api/v1/simulation/{simulation_id}/steps`

Get step-by-step data for a simulation.

**Path Parameters:**
- `simulation_id` (string): The simulation ID.

**Query Parameters:**
- `offset` (int, default: 0): Number of steps to skip.
- `limit` (int, default: 100): Maximum number of steps to return.

**Response:**
```json
{
  "simulation_id": "uuid-string",
  "total_steps": 200,
  "offset": 0,
  "limit": 100,
  "steps": [
    {
      "step": 0,
      "price": 100.0,
      "fear": 0.3,
      "greed": 0.3,
      "confidence": 0.5,
      "uncertainty": 0.3,
      "buy_count": 15,
      "sell_count": 10,
      "hold_count": 55,
      "reflexivity_index": 0.12,
      "bubble_risk": 0.05,
      "regime": "normal"
    }
  ]
}
```

---

#### `GET /api/v1/simulations`

List all completed simulations.

**Response:**
```json
{
  "simulations": [
    {
      "id": "uuid-string",
      "status": "completed",
      "created_at": "2026-05-29T10:00:00Z",
      "n_steps": 200,
      "final_price": 125.34
    }
  ],
  "total": 1
}
```

---

### Narrative

#### `POST /api/v1/narrative/inject`

Inject a narrative event into the simulation.

**Request Body:**
```json
{
  "name": "AI Healthcare Revolution",
  "category": "fintech",
  "polarity": "positive",
  "intensity": 0.7,
  "credibility": 0.8,
  "duration": 20
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Narrative event name |
| `category` | string | "sentiment" | Category: policy, sector, macro, fintech, regulatory, earnings |
| `polarity` | string | required | positive, negative, or neutral |
| `intensity` | float | 0.5 | Narrative intensity (0.0-1.0) |
| `credibility` | float | 0.6 | Narrative credibility (0.0-1.0) |
| `duration` | int | 20 | Duration in steps (1-200) |

**Response:**
```json
{
  "status": "injected",
  "narrative": {
    "id": "uuid-string",
    "name": "AI Healthcare Revolution",
    "category": "fintech",
    "polarity": "positive",
    "intensity": 0.7,
    "credibility": 0.8,
    "duration": 20
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid polarity or category value.

---

### Market State

#### `GET /api/v1/market/state`

Get the current market state.

**Response:**
```json
{
  "market": {
    "price": 125.34,
    "initial_price": 100.0,
    "fundamental_value": 100.0,
    "price_change_pct": 0.015,
    "volatility": 0.023,
    "order_imbalance": 0.12,
    "step_count": 150
  },
  "emotion": {
    "fear": 0.25,
    "greed": 0.45,
    "confidence": 0.60,
    "uncertainty": 0.30,
    "fear_greed_index": 0.20
  }
}
```

---

### Agents

#### `GET /api/v1/agents/summary`

Get summary information about the agent population.

**Response:**
```json
{
  "agent_types": [
    {
      "type": "value_investor",
      "count": 10,
      "description": "Fundamental-value-driven, contrarian strategy",
      "characteristics": {
        "herding_coefficient": 0.1,
        "emotional_sensitivity": 0.2
      }
    },
    {
      "type": "trend_follower",
      "count": 20,
      "description": "Momentum-driven, emotion-amplified strategy",
      "characteristics": {
        "herding_coefficient": 0.4,
        "emotional_sensitivity": 0.4
      }
    },
    {
      "type": "emotional_retail",
      "count": 50,
      "description": "FOMO/panic-driven, high information lag",
      "characteristics": {
        "herding_coefficient": 0.7,
        "emotional_sensitivity": 0.8
      }
    }
  ],
  "network_structure": {
    "total_nodes": 117,
    "kol_tiers": ["macro", "influencer", "micro", "retail"]
  },
  "reflexivity_model": {
    "belief_update": "BeliefUpdaterV2 (5-factor model)",
    "causal_chain": "Narrative -> Belief -> Emotion -> Behavior -> Capital -> Price"
  }
}
```

---

### WebSocket

#### `WS /ws`

Real-time simulation data stream.

**Messages:**

Subscribe to simulation updates:
```json
{
  "type": "subscribe",
  "channel": "simulation",
  "simulation_id": "uuid-string"
}
```

Receive step updates:
```json
{
  "type": "step_update",
  "simulation_id": "uuid-string",
  "step": 150,
  "data": {
    "price": 125.34,
    "reflexivity_index": 0.45,
    "bubble_risk": 0.32,
    "regime": "bubble_forming"
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource does not exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |

---

## Data Models

### NarrativeCategory

| Value | Description |
|-------|-------------|
| `policy` | Policy announcements |
| `sector` | Sector-specific news |
| `macro` | Macroeconomic events |
| `fintech` | Technology/AI narratives |
| `regulatory` | Regulatory changes |
| `earnings` | Earnings/data releases |
| `manipulation` | Abnormal narratives (risk simulation) |
| `sentiment` | Market sentiment |

### Polarity

| Value | Description |
|-------|-------------|
| `positive` | Bullish narrative |
| `negative` | Bearish narrative |
| `neutral` | Neutral/ambiguous |

### MarketRegime

| Value | Description |
|-------|-------------|
| `normal` | Normal market conditions |
| `bubble_forming` | Early bubble formation |
| `bubble_peak` | Bubble at peak |
| `crash` | Market crash |
| `panic_spread` | Panic spreading |
| `recovery` | Recovery phase |
