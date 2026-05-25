# WattOps

Cloud-native solar and battery optimization for Growatt inverters

## Overview

This project provides a Growatt controller to optimize a residential solar setup.

The solution includes two components:

- Planner
- Executor

## Planning Logic

The planner runs every night and evaluates the next day's electricity prices.

If the price exceeds a defined threshold, the planner should disable export on the Growatt inverter.

If the expected solar panel output (based on weather and seasonality) is greater than approximately 20 kWh, the system should enable Grid First mode starting at 06:00 for an appropriate duration.

The output threshold (for example, 20 kWh) should be configurable.

Solar production forecasts should come from one or more external APIs. If multiple forecast sources are used, the system can compare them and use an average value.

## Azure Architecture

The system should run on Azure using Azure Functions.

It should also use:

- Azure Key Vault for storing the Growatt API key
- Azure Service Bus for planned action messages

The planner publishes messages, and the executor applies those actions to Growatt.

Recommendation: implement this as a single Azure Function App containing two functions.

## Technology

Build the solution in Python using the latest stable version available for Azure Functions.

## Example Message Schema

```json
{
  "schema_version": "1.0",
  "message_id": "uuid",
  "correlation_id": "plan-2026-05-25",
  "command": {
    "name": "set_export_limit",
    "value": 0,
    "unit": "percent"
  },
  "window": {
    "start": "2026-05-25T11:00:00Z",
    "end": "2026-05-25T14:00:00Z"
  },
  "reason": {
    "type": "negative_price",
    "details": {
      "price": 0.03,
      "forecast_kwh": 24
    }
  },
  "target": {
    "site_id": "home-1",
    "device_id": "growatt-1"
  },
  "policy": {
    "priority": 5,
    "allow_override": true,
    "min_duration_minutes": 30
  },
  "created_at": "2026-05-24T23:01:00Z"
}
```
