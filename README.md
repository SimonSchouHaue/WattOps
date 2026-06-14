# ⚡ WattOps

> Automated smart home energy optimization for Growatt solar inverters — powered by Azure Functions.

WattOps is a serverless energy management system that automatically optimizes battery charge/discharge cycles and grid export based on real-time electricity prices and solar production forecasts. Every evening it plans the next day's energy actions and schedules them to execute at the right moment.

---

## 🧠 How It Works

```
Every day at 23:00
       │
       ▼
  📋 Planner Function
       ├── Fetches tomorrow's electricity prices (Energi Data Service)
       ├── Fetches solar forecasts (OpenMeteo + ForecastSolar)
       └── Schedules optimized actions on Azure Service Bus
                          │
                          ▼ (at scheduled time)
                  ⚙️ Executor Function
                          └── Applies commands to Growatt inverter via API
```

### 🔋 What Gets Optimized

| Scenario                       | Action                                      |
| ------------------------------ | ------------------------------------------- |
| Electricity price is **cheap** | Limit grid export, charge battery from grid |
| Solar forecast is **high**     | Enable grid-first mode (sell/use solar)     |
| Solar forecast is **low**      | Disable grid-first mode, prioritize grid    |
| Morning peak hours             | Grid-first mode for configurable duration   |

---

## 🏗️ Architecture

```
WattOps/
├── src/                        # Azure Functions app (Python)
│   ├── function_app.py         # Function entry points (planner + executor)
│   ├── functions/
│   │   ├── planner.py          # Planning logic & action generation
│   │   └── executor.py         # Growatt command execution
│   ├── services/
│   │   ├── forecast/           # Solar forecast providers
│   │   ├── growatt/            # Growatt inverter API client
│   │   └── price/              # Electricity price providers
│   ├── models/                 # Shared data models
│   └── utils/
│       └── config.py           # Settings loaded from environment variables
└── IaC/                        # Bicep infrastructure-as-code
    ├── main.bicep
    └── modules/                # Azure resource modules
```

### ☁️ Azure Resources

Provisioned via Bicep:

- **Azure Function App** — Hosts the planner & executor functions
- **Azure Service Bus** — Transports and schedules planned actions
- **Azure Key Vault** — Stores secrets (Growatt API key)
- **Azure Storage Account** — Function App deployment & state storage
- **Azure Managed Identity** — Passwordless auth between Azure services
- **Azure Application Insights** — Logging & monitoring

---

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- Azure subscription (for deployment)

### Local Development

1. **Install dependencies**

   ```bash
   cd src
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Copy `local.settings.json` and fill in your values:

   ```jsonc
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",

       // Growatt inverter credentials
       "GROWATT_API_KEY": "<your-growatt-api-key>",
       "GROWATT_DEVICE_SERIAL_NUMBER": "<your-device-sn>",
       "GROWATT_DISCHARGE_POWER_PERCENT": "50", // discharge power during grid-first window (%)
       "GROWATT_STOP_SOC_PERCENT": "25", // stop discharging during grid-first when battery reaches this level (%)

       // Electricity pricing
       "PRICE_AREA": "DK1", // price area, e.g. DK1 or DK2
       "PRICE_EXPORT_THRESHOLD_DKK_KWH": "0.10", // limit export when the sport price is below the threshold (DKK/kWh)

       // Solar panel setup
       "SOLAR_LATITUDE": "55.0", // latitude where the solar panel is installed
       "SOLAR_LONGITUDE": "10.0", // longitude where the solar panel is installed
       "SOLAR_OUTPUT_THRESHOLD_KWH": "20", // min forecast (kWh) to enable discharge
       "SOLAR_PANEL_KWP": "5.0", // installed capacity
       "SOLAR_PANEL_TILT": "35", // tilt angle in degrees
       "SOLAR_PANEL_AZIMUTH": "0", // 0 = south
       "SOLAR_PERFORMANCE_RATIO": "0.90", // system efficiency ratio

       // Grid-first morning window
       "GRID_FIRST_START_HOUR": "6", // hour of day to start
       "GRID_FIRST_MIN_MINUTES": "60", // minimum window duration
       "GRID_FIRST_MAX_MINUTES": "360", // maximum window duration

       // Azure Service Bus
       "PLANNER_QUEUE_NAME": "planned-actions",
       "ServiceBusConnection__fullyQualifiedNamespace": "<your-servicebus>.servicebus.windows.net",

       // Safety: set to "false" to actually send commands to the inverter
       "DRY_RUN": "true",
     },
   }
   ```

3. **Start the function host**

   ```bash
   cd src
   func host start
   ```

---

## 🌐 External Services

| Service                                                  | Purpose                                                    |
| -------------------------------------------------------- | ---------------------------------------------------------- |
| [Energi Data Service](https://www.energidataservice.dk/) | Danish electricity spot prices                             |
| [Open-Meteo](https://open-meteo.com/)                    | Weather-based solar irradiance forecast                    |
| [Forecast.Solar](https://forecast.solar/)                | Solar production forecast                                  |
| [Growatt API](https://www.growatt.com/)                  | Inverter control (export limits, charge/discharge windows) |

---

## 🔒 Security

- Secrets are stored in **Azure Key Vault** — never in code or config files
- The Function App authenticates to Azure services using a **Managed Identity** (no stored credentials)
- `DRY_RUN=true` is the safe default — no inverter commands are sent until explicitly enabled
