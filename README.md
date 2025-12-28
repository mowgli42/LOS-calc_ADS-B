# ADS-B Line of Sight Calculator

A minimalistic web interface for calculating line-of-sight distances between aircraft from ADS-B data and analyzing multi-hop communication paths.

## Features

- Real-time aircraft data ingestion from OpenSky Network API
- Radio horizon line-of-sight distance calculations
- Multi-hop communication path analysis (direct, 1-hop, 2-hop, 3-hop)
- Carrier filtering for top 25 worldwide airlines
- Carrier-specific communication range configuration
- Automatic data refresh every 15 minutes
- Minimalistic dark theme UI with green accents

## Requirements

- Python 3.8+
- pip

## Installation

1. Clone the repository:
```bash
cd LOS-calc_ADS-B
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Configuration

### Carrier Communication Ranges

Carrier-specific communication ranges can be configured in the web interface. Default ranges are defined in `config.py` and can be adjusted per-carrier through the configuration panel.

### Top 25 Supported Carriers

- American Airlines (AAL)
- Delta Air Lines (DAL)
- United Airlines (UAL)
- Southwest Airlines (SWA)
- Lufthansa (DLH)
- British Airways (BAW)
- Air France (AFR)
- Emirates (UAE)
- Qatar Airways (QTR)
- Singapore Airlines (SIA)
- Japan Airlines (JAL)
- KLM Royal Dutch Airlines (KLM)
- Iberia (IBE)
- All Nippon Airways (ANA)
- Thai Airways (THA)
- Qantas (QFA)
- LATAM (TAM)
- Turkish Airlines (TUR)
- Etihad Airways (ETD)
- Cathay Pacific (CXA)
- China Southern (CSN)
- China Eastern (CES)
- China Airlines (CAL)
- Korean Air (KAL)
- Virgin Atlantic (VIR)

## API Endpoints

### `GET /api/aircraft`
Returns all available aircraft data filtered to top 25 carriers.

### `POST /api/distances`
Calculates distances for selected carriers.

**Request Body:**
```json
{
  "carriers": ["DAL", "UAL", "SWA"],
  "carrier_ranges": {
    "DAL": 200,
    "UAL": 200
  }
}
```

**Response:**
```json
{
  "distances": [...],
  "aircraft_count": 42,
  "total_pairs": 861,
  "bins": {
    "0-50": 120,
    "50-100": 200,
    ...
  }
}
```

### `POST /api/communication`
Returns communication path statistics.

**Request Body:**
```json
{
  "carriers": ["DAL", "UAL"],
  "carrier_ranges": {
    "DAL": 200,
    "UAL": 200
  }
}
```

**Response:**
```json
{
  "direct": 45,
  "1hop": 120,
  "2hop": 200,
  "3hop": 180,
  "aircraft_count": 42
}
```

### `GET /api/carriers`
Returns list of available carriers with default communication ranges.

## Architecture

- **Backend**: Python Flask with REST API
- **Frontend**: HTML/CSS/JavaScript with Chart.js
- **Data Source**: OpenSky Network API
- **Distance Calculation**: Radio horizon formula accounting for Earth curvature
- **Graph Analysis**: Breadth-first search for multi-hop path discovery

## File Structure

```
LOS-calc_ADS-B/
├── app.py                    # Flask application
├── config.py                 # Configuration settings
├── data_ingester.py          # OpenSky API client
├── distance_calculator.py    # LOS distance calculations
├── communication_analyzer.py # Multi-hop analysis
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Web interface
└── static/
    ├── css/
    │   └── style.css        # Dark theme styling
    └── js/
        └── main.js          # Frontend logic
```

## License

This project is provided as-is for educational and research purposes.

